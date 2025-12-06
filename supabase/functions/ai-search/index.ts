import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { query, mode, context, previousResults } = await req.json();
    const LOVABLE_API_KEY = Deno.env.get("LOVABLE_API_KEY");
    
    if (!LOVABLE_API_KEY) {
      throw new Error("LOVABLE_API_KEY is not configured");
    }

    const authHeader = req.headers.get("Authorization");
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseKey = Deno.env.get("SUPABASE_ANON_KEY")!;
    
    const supabase = createClient(supabaseUrl, supabaseKey, {
      global: { headers: { Authorization: authHeader! } }
    });

    let labData = null;
    let results: any[] = [];

    // Fetch lab data for context if in lab mode
    if (mode === "lab") {
      const [experiments, protocols, orders] = await Promise.all([
        supabase.from("experiments").select("id, title, description, status").limit(20),
        supabase.from("protocols").select("id, title, description, usage_count").limit(20),
        supabase.from("orders").select("id, item_name, vendor, status, notes").limit(20),
      ]);

      labData = {
        experiments: experiments.data || [],
        protocols: protocols.data || [],
        orders: orders.data || [],
      };
    }

    // Build the system prompt based on mode
    let systemPrompt = "";
    
    if (mode === "lab") {
      systemPrompt = `You are an AI assistant for a research lab workspace. You help researchers find experiments, protocols, and orders.

Here is the current lab data:
${JSON.stringify(labData, null, 2)}

When searching:
1. Find relevant items based on the user's query
2. Provide a brief, helpful summary of what you found
3. For follow-up questions, use the context of previous results

Always be concise and helpful. Format your response as JSON with:
- "summary": A brief conversational summary (2-3 sentences max)
- "results": An array of relevant items with type, id, title, and description`;
    } else {
      systemPrompt = `You are an AI assistant that helps researchers find academic papers. 

When the user asks about a research topic:
1. Generate realistic academic paper results based on the query
2. Provide a brief AI summary of the research landscape
3. Include paper titles, brief descriptions, and realistic Google Scholar URLs

Format your response as JSON with:
- "summary": A brief conversational summary about the research topic (2-3 sentences)
- "results": An array of papers with type: "scholar", title, description, and url (use format https://scholar.google.com/scholar?q=...)`;
    }

    const messages: any[] = [
      { role: "system", content: systemPrompt }
    ];

    // Add conversation context if provided
    if (context && Array.isArray(context)) {
      for (const msg of context) {
        messages.push({ role: msg.role, content: msg.content });
      }
    } else {
      messages.push({ role: "user", content: query });
    }

    // Add previous results context if available
    if (previousResults && previousResults.length > 0) {
      messages.push({
        role: "system",
        content: `Previous search results for context: ${JSON.stringify(previousResults)}`
      });
    }

    const response = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${LOVABLE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "google/gemini-2.5-flash",
        messages,
        response_format: { type: "json_object" },
      }),
    });

    if (!response.ok) {
      if (response.status === 429) {
        return new Response(JSON.stringify({ error: "Rate limit exceeded. Please try again later." }), {
          status: 429,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      if (response.status === 402) {
        return new Response(JSON.stringify({ error: "AI credits exhausted. Please add credits." }), {
          status: 402,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      throw new Error(`AI gateway error: ${response.status}`);
    }

    const aiResponse = await response.json();
    const content = aiResponse.choices?.[0]?.message?.content;

    let parsed;
    try {
      parsed = JSON.parse(content);
    } catch {
      parsed = { summary: content, results: [] };
    }

    return new Response(JSON.stringify(parsed), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("AI search error:", error);
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : "Unknown error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
