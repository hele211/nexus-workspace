"""
Reagent tools for discovery, registration, and inventory management.

Provides tools for:
- SearchReagentOnlineTool: Search web for reagent products via Tavily
- GetReagentDetailsFromWebTool: Get detailed info for a specific product
- AddReagentToInventoryTool: Register reagent in inventory
- RecordReagentUsageTool: Track reagent usage and low-inventory alerts
- ListLowInventoryReagentsTool: List reagents below 10% remaining

All tools follow SpoonOS BaseTool patterns with async execute methods.
"""

import re
from typing import Any, Dict, List, Optional

from spoon_ai.tools.base import BaseTool

from backend import config
from backend.services.reagent_service import get_reagent_service


# =============================================================================
# Tavily Search Tools
# =============================================================================

class SearchReagentOnlineTool(BaseTool):
    """
    Search the web for reagent products using Tavily API.
    
    Finds antibodies, chemicals, and other lab reagents from vendors
    and returns a ranked list of candidates.
    """
    
    name: str = "search_reagent_online"
    description: str = """Search the web for reagent products (antibodies, chemicals, etc.).
Use this when a user asks to find or search for a reagent like "mouse CD64 antibody".
Returns a ranked list of product candidates with vendor info and URLs."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for the reagent (e.g., 'mouse anti-CD64 antibody')"
            }
        },
        "required": ["query"]
    }
    
    async def execute(self, query: str, **kwargs) -> str:
        """
        Search for reagent products online.
        
        Args:
            query: Search query for the reagent
            
        Returns:
            Formatted string with ranked list of candidates
        """
        if not config.TAVILY_API_KEY:
            return """❌ **Tavily API not configured**

To enable reagent search, add your Tavily API key to `.env`:
```
TAVILY_API_KEY=your_api_key_here
```

Get an API key at: https://tavily.com/"""
        
        try:
            from tavily import TavilyClient
            
            client = TavilyClient(api_key=config.TAVILY_API_KEY)
            
            # Search with focus on reagent/product pages
            search_query = f"{query} reagent product catalog buy"
            
            response = client.search(
                query=search_query,
                search_depth="basic",
                max_results=5,
                include_domains=[
                    "thermofisher.com",
                    "abcam.com", 
                    "biolegend.com",
                    "sigmaaldrich.com",
                    "cellsignal.com",
                    "rndsystems.com",
                    "bdbiosciences.com"
                ]
            )
            
            results = response.get("results", [])
            
            if not results:
                return f"""🔍 **No results found for:** {query}

Try:
- Using more specific terms (e.g., "mouse anti-CD64 monoclonal antibody")
- Including the target species
- Checking spelling"""
            
            # Parse and format results
            candidates = []
            for i, result in enumerate(results):
                title = result.get("title", "Unknown Product")
                url = result.get("url", "")
                content = result.get("content", "")
                
                # Try to extract vendor from URL
                vendor = self._extract_vendor(url)
                
                # Try to extract catalog number from content/title
                catalog = self._extract_catalog_number(title + " " + content)
                
                candidates.append({
                    "rank": i + 1,
                    "title": title[:100],
                    "vendor": vendor,
                    "catalog_number": catalog,
                    "url": url
                })
            
            # Format response
            response_lines = [f"🔬 **Reagent Search Results for:** {query}\n"]
            
            # Top recommendation
            top = candidates[0]
            response_lines.append("## ⭐ Top Recommendation\n")
            response_lines.append(f"**{top['title']}**")
            response_lines.append(f"- Vendor: {top['vendor']}")
            if top['catalog_number']:
                response_lines.append(f"- Catalog #: {top['catalog_number']}")
            response_lines.append(f"- URL: {top['url']}")
            response_lines.append("")
            
            # Other candidates
            if len(candidates) > 1:
                response_lines.append("## Other Options\n")
                for c in candidates[1:]:
                    response_lines.append(f"**{c['rank']}. {c['title']}**")
                    response_lines.append(f"   - Vendor: {c['vendor']}")
                    if c['catalog_number']:
                        response_lines.append(f"   - Catalog #: {c['catalog_number']}")
                    response_lines.append(f"   - URL: {c['url']}")
                    response_lines.append("")
            
            response_lines.append("---")
            response_lines.append("💡 To add a reagent to inventory, tell me which one you'd like and I'll get the details.")
            
            return "\n".join(response_lines)
            
        except ImportError:
            return """❌ **Tavily package not installed**

Install with: `pip install tavily-python`"""
        except Exception as e:
            return f"❌ **Search error:** {str(e)}"
    
    def _extract_vendor(self, url: str) -> str:
        """Extract vendor name from URL."""
        vendor_map = {
            "thermofisher": "Thermo Fisher",
            "abcam": "Abcam",
            "biolegend": "BioLegend",
            "sigmaaldrich": "Sigma-Aldrich",
            "cellsignal": "Cell Signaling",
            "rndsystems": "R&D Systems",
            "bdbiosciences": "BD Biosciences",
            "invitrogen": "Invitrogen",
            "millipore": "Millipore"
        }
        url_lower = url.lower()
        for key, name in vendor_map.items():
            if key in url_lower:
                return name
        return "Unknown Vendor"
    
    def _extract_catalog_number(self, text: str) -> Optional[str]:
        """Try to extract catalog number from text."""
        # Common patterns: AB-123456, #12345, Cat# 12345
        patterns = [
            r"[A-Z]{2,3}[-_]?\d{4,8}",  # AB-123456
            r"#\s*(\d{4,8})",            # #12345
            r"Cat\.?\s*#?\s*(\w{4,12})", # Cat# 12345
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None


class GetReagentDetailsFromWebTool(BaseTool):
    """
    Get detailed information for a specific reagent product.
    
    Uses Tavily to enrich metadata for a product identified by
    catalog number, vendor, or product URL.
    """
    
    name: str = "get_reagent_details_from_web"
    description: str = """Get detailed information for a specific reagent product.
Use this after the user selects a product from search results.
Provide catalog number, vendor, or product URL to get full details."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "catalog_number": {
                "type": "string",
                "description": "Product catalog number"
            },
            "vendor": {
                "type": "string",
                "description": "Vendor/supplier name"
            },
            "product_url": {
                "type": "string",
                "description": "Direct URL to product page"
            }
        },
        "required": []
    }
    
    async def execute(
        self,
        catalog_number: Optional[str] = None,
        vendor: Optional[str] = None,
        product_url: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Get detailed reagent information.
        
        Args:
            catalog_number: Product catalog number
            vendor: Vendor name
            product_url: Direct product URL
            
        Returns:
            Formatted string with reagent details
        """
        # Validate at least one parameter provided
        if not any([catalog_number, vendor, product_url]):
            return """❌ **Missing information**

Please provide at least one of:
- Catalog number
- Vendor name
- Product URL"""
        
        if not config.TAVILY_API_KEY:
            return """❌ **Tavily API not configured**

Add TAVILY_API_KEY to your `.env` file."""
        
        try:
            from tavily import TavilyClient
            
            client = TavilyClient(api_key=config.TAVILY_API_KEY)
            
            # Build search query
            query_parts = []
            if catalog_number:
                query_parts.append(catalog_number)
            if vendor:
                query_parts.append(vendor)
            query_parts.append("reagent product specifications storage")
            
            search_query = " ".join(query_parts)
            
            # If URL provided, try to extract content from it
            if product_url:
                response = client.search(
                    query=search_query,
                    search_depth="advanced",
                    max_results=3,
                    include_domains=[self._extract_domain(product_url)]
                )
            else:
                response = client.search(
                    query=search_query,
                    search_depth="advanced",
                    max_results=3
                )
            
            results = response.get("results", [])
            
            if not results:
                return f"""❌ **No details found**

Could not find detailed information for:
- Catalog #: {catalog_number or 'N/A'}
- Vendor: {vendor or 'N/A'}
- URL: {product_url or 'N/A'}"""
            
            # Extract details from results
            combined_content = " ".join([r.get("content", "") for r in results])
            first_result = results[0]
            
            # Parse details
            details = {
                "name": first_result.get("title", "Unknown"),
                "catalog_number": catalog_number or self._extract_field(combined_content, "catalog"),
                "vendor": vendor or self._extract_vendor_from_url(first_result.get("url", "")),
                "storage_conditions": self._extract_storage(combined_content),
                "quantity": self._extract_quantity(combined_content),
                "url": product_url or first_result.get("url", "")
            }
            
            # Format response
            return f"""📋 **Reagent Details**

**Name:** {details['name']}
**Catalog #:** {details['catalog_number'] or 'Not found'}
**Vendor:** {details['vendor']}
**Storage:** {details['storage_conditions']}
**Pack Size:** {details['quantity']}
**URL:** {details['url']}

---
💡 To add this to your inventory, say "add this reagent" or provide the initial quantity."""
            
        except ImportError:
            return "❌ **Tavily package not installed.** Run: `pip install tavily-python`"
        except Exception as e:
            return f"❌ **Error getting details:** {str(e)}"
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        import re
        match = re.search(r"https?://(?:www\.)?([^/]+)", url)
        return match.group(1) if match else ""
    
    def _extract_vendor_from_url(self, url: str) -> str:
        """Extract vendor from URL."""
        vendor_map = {
            "thermofisher": "Thermo Fisher",
            "abcam": "Abcam",
            "biolegend": "BioLegend",
            "sigmaaldrich": "Sigma-Aldrich",
            "cellsignal": "Cell Signaling"
        }
        url_lower = url.lower()
        for key, name in vendor_map.items():
            if key in url_lower:
                return name
        return "Unknown"
    
    def _extract_field(self, text: str, field_type: str) -> Optional[str]:
        """Extract field from text."""
        if field_type == "catalog":
            match = re.search(r"[A-Z]{2,3}[-_]?\d{4,8}", text)
            return match.group(0) if match else None
        return None
    
    def _extract_storage(self, text: str) -> str:
        """Extract storage conditions from text."""
        patterns = [
            r"store\s+at\s+([^.]+)",
            r"storage[:\s]+([^.]+)",
            r"(-?\d+\s*°?C)",
            r"(room temperature|refrigerat|frozen|freeze)"
        ]
        text_lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                if "°c" in result.lower() or "temperature" in result.lower():
                    return result.title()
        return "Check product documentation"
    
    def _extract_quantity(self, text: str) -> str:
        """Extract quantity/pack size from text."""
        patterns = [
            r"(\d+\s*(?:µ[gL]|mg|mL|g|L|units?))",
            r"pack\s*size[:\s]*(\d+\s*\w+)",
            r"(\d+\s*tests?)"
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return "Check product page"


# =============================================================================
# Inventory Management Tools
# =============================================================================

class AddReagentToInventoryTool(BaseTool):
    """
    Add a reagent to the lab inventory.
    
    Creates or updates a reagent record with structured metadata.
    """
    
    name: str = "add_reagent_to_inventory"
    description: str = """Add a reagent to the lab inventory.
Use this after getting reagent details to register it in the inventory system.
Requires name, catalog number, vendor, storage conditions, quantity, and unit."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Reagent name"
            },
            "catalog_number": {
                "type": "string",
                "description": "Vendor catalog number"
            },
            "vendor": {
                "type": "string",
                "description": "Vendor/supplier name"
            },
            "storage_conditions": {
                "type": "string",
                "description": "Storage requirements (e.g., '-20°C', 'Room temperature')"
            },
            "initial_quantity": {
                "type": "number",
                "description": "Initial quantity"
            },
            "unit": {
                "type": "string",
                "description": "Unit of measurement (e.g., 'µL', 'mg', 'mL')"
            }
        },
        "required": ["name", "catalog_number", "vendor", "storage_conditions", "initial_quantity", "unit"]
    }
    
    async def execute(
        self,
        name: str,
        catalog_number: str,
        vendor: str,
        storage_conditions: str,
        initial_quantity: float,
        unit: str,
        **kwargs
    ) -> str:
        """
        Add reagent to inventory.
        
        Args:
            name: Reagent name
            catalog_number: Catalog number
            vendor: Vendor name
            storage_conditions: Storage requirements
            initial_quantity: Initial quantity
            unit: Unit of measurement
            
        Returns:
            Confirmation message with reagent_id
        """
        try:
            service = get_reagent_service()
            
            reagent = service.create_reagent(
                name=name,
                catalog_number=catalog_number,
                vendor=vendor,
                storage_conditions=storage_conditions,
                initial_quantity=initial_quantity,
                unit=unit
            )
            
            return f"""✅ **Reagent Added to Inventory**

**Reagent ID:** `{reagent['reagent_id']}`
**Name:** {reagent['name']}
**Catalog #:** {reagent['catalog_number']}
**Vendor:** {reagent['vendor']}
**Storage:** {reagent['storage_conditions']}
**Quantity:** {reagent['current_quantity']} {reagent['unit']}

---
💡 Use the reagent ID to record usage: "I used 5 {unit} of {reagent['reagent_id']}"
"""
            
        except Exception as e:
            return f"❌ **Error adding reagent:** {str(e)}"


class RecordReagentUsageTool(BaseTool):
    """
    Record reagent usage and update inventory.
    
    Decrements quantity and warns if inventory falls below 10%.
    """
    
    name: str = "record_reagent_usage"
    description: str = """Record that a reagent was used in an experiment.
Updates the inventory quantity and warns if running low (<10% remaining).
Requires reagent_id, amount used, and unit."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "reagent_id": {
                "type": "string",
                "description": "Reagent ID (e.g., 'reagent_abc123')"
            },
            "amount_used": {
                "type": "number",
                "description": "Amount used"
            },
            "unit": {
                "type": "string",
                "description": "Unit of measurement (must match reagent's unit)"
            },
            "experiment_id": {
                "type": "string",
                "description": "Optional experiment ID for tracking"
            }
        },
        "required": ["reagent_id", "amount_used", "unit"]
    }
    
    async def execute(
        self,
        reagent_id: str,
        amount_used: float,
        unit: str,
        experiment_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Record reagent usage.
        
        Args:
            reagent_id: Reagent ID
            amount_used: Amount used
            unit: Unit of measurement
            experiment_id: Optional experiment ID
            
        Returns:
            Usage confirmation with before/after quantities
        """
        try:
            service = get_reagent_service()
            
            result = service.record_usage(
                reagent_id=reagent_id,
                amount_used=amount_used,
                unit=unit,
                experiment_id=experiment_id
            )
            
            # Build response
            response_lines = [
                "📝 **Reagent Usage Recorded**",
                "",
                f"**Reagent:** {result['reagent_name']}",
                f"**Amount Used:** {result['amount_used']} {result['unit']}",
                f"**Before:** {result['before_quantity']} {result['unit']}",
                f"**After:** {result['after_quantity']} {result['unit']}",
                f"**Remaining:** {result['remaining_percentage']}%"
            ]
            
            if result['experiment_id']:
                response_lines.append(f"**Experiment:** {result['experiment_id']}")
            
            # Low inventory warning
            if result['low_inventory']:
                response_lines.extend([
                    "",
                    "⚠️ **LOW INVENTORY WARNING**",
                    f"Less than 10% remaining ({result['remaining_percentage']}%)",
                    "Consider reordering this reagent soon!"
                ])
            
            return "\n".join(response_lines)
            
        except ValueError as e:
            return f"❌ **Error:** {str(e)}"
        except Exception as e:
            return f"❌ **Error recording usage:** {str(e)}"


class ListLowInventoryReagentsTool(BaseTool):
    """
    List reagents with low inventory (<10% remaining).
    
    Helps identify reagents that need to be reordered.
    """
    
    name: str = "list_low_inventory_reagents"
    description: str = """List all reagents with low inventory (less than 10% remaining).
Use this when the user asks about inventory status or what needs to be reordered."""
    
    parameters: dict = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    async def execute(self, **kwargs) -> str:
        """
        List low inventory reagents.
        
        Returns:
            Formatted list of low inventory reagents
        """
        try:
            service = get_reagent_service()
            
            low_inventory = service.get_low_inventory_reagents()
            
            if not low_inventory:
                return """✅ **No Low-Inventory Reagents**

All reagents are above 10% remaining. Inventory looks good!"""
            
            # Format response
            response_lines = [
                f"⚠️ **Low Inventory Alert: {len(low_inventory)} reagent(s) below 10%**",
                ""
            ]
            
            for reagent in low_inventory:
                response_lines.extend([
                    f"**{reagent['name']}**",
                    f"  - Vendor: {reagent['vendor']}",
                    f"  - Catalog #: {reagent['catalog_number']}",
                    f"  - Remaining: {reagent['current_quantity']} / {reagent['initial_quantity']} {reagent['unit']} ({reagent['remaining_percentage']}%)",
                    ""
                ])
            
            response_lines.append("---")
            response_lines.append("💡 Consider reordering these reagents soon.")
            
            return "\n".join(response_lines)
            
        except Exception as e:
            return f"❌ **Error checking inventory:** {str(e)}"


# Export all tools
__all__ = [
    "SearchReagentOnlineTool",
    "GetReagentDetailsFromWebTool",
    "AddReagentToInventoryTool",
    "RecordReagentUsageTool",
    "ListLowInventoryReagentsTool",
]
