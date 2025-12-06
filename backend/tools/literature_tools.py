"""
Literature search tools for the LiteratureAgent.

Provides tools for searching academic databases:
- PubMedSearchTool: Biomedical/life sciences (NCBI)
- SemanticScholarTool: All disciplines (200M+ papers)

Both tools follow SpoonOS BaseTool patterns with async execute methods.
"""

import asyncio
from typing import Dict, List, Optional

import requests
from Bio import Entrez
from spoon_ai.tools.base import BaseTool

from backend import config


class PubMedSearchTool(BaseTool):
    """
    Search PubMed for biomedical research papers.
    
    Uses NCBI Entrez API with configured email and API key.
    Best for: medical protocols, drug information, clinical studies,
    biology research, life sciences.
    """
    
    name: str = "search_pubmed"
    description: str = (
        "Search PubMed for biomedical research papers. "
        "Use for: medical protocols, drug information, clinical studies, "
        "biology research. Example: 'PCR optimization protocols'"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for PubMed"
            },
            "max_results": {
                "type": "integer",
                "default": 10,
                "description": "Number of papers to return (1-50)"
            },
            "sort": {
                "type": "string",
                "enum": ["relevance", "pub_date"],
                "default": "relevance",
                "description": "Sort order for results"
            }
        },
        "required": ["query"]
    }

    async def execute(
        self,
        query: str,
        max_results: int = 10,
        sort: str = "relevance"
    ) -> str:
        """
        Execute PubMed search and return formatted results.
        
        Args:
            query: Search query string
            max_results: Number of results to return (1-50)
            sort: Sort order ('relevance' or 'pub_date')
            
        Returns:
            Formatted string with paper details or error message
        """
        try:
            # Configure Entrez
            Entrez.email = config.NCBI_EMAIL
            if config.NCBI_API_KEY:
                Entrez.api_key = config.NCBI_API_KEY
            
            # Clamp max_results
            max_results = max(1, min(50, max_results))
            
            # Run blocking Entrez calls in executor
            loop = asyncio.get_event_loop()
            
            # Search for paper IDs
            def do_search():
                handle = Entrez.esearch(
                    db="pubmed",
                    term=query,
                    retmax=max_results,
                    sort=sort
                )
                results = Entrez.read(handle)
                handle.close()
                return results
            
            search_results = await loop.run_in_executor(None, do_search)
            id_list = search_results.get("IdList", [])
            
            if not id_list:
                return f"No papers found in PubMed for query: '{query}'"
            
            # Fetch paper details
            def do_fetch():
                handle = Entrez.efetch(
                    db="pubmed",
                    id=",".join(id_list),
                    rettype="xml",
                    retmode="xml"
                )
                records = Entrez.read(handle)
                handle.close()
                return records
            
            records = await loop.run_in_executor(None, do_fetch)
            
            # Parse and format results
            papers = []
            articles = records.get("PubmedArticle", [])
            
            for i, article in enumerate(articles, 1):
                try:
                    medline = article.get("MedlineCitation", {})
                    article_data = medline.get("Article", {})
                    
                    # Extract fields
                    title = article_data.get("ArticleTitle", "No title")
                    
                    # Authors (first 3)
                    author_list = article_data.get("AuthorList", [])
                    authors = []
                    for author in author_list[:3]:
                        last = author.get("LastName", "")
                        first = author.get("ForeName", "")
                        if last:
                            authors.append(f"{last} {first}".strip())
                    authors_str = ", ".join(authors) if authors else "Unknown"
                    if len(author_list) > 3:
                        authors_str += " et al."
                    
                    # Journal and year
                    journal_info = article_data.get("Journal", {})
                    journal = journal_info.get("Title", "Unknown Journal")
                    pub_date = journal_info.get("JournalIssue", {}).get("PubDate", {})
                    year = pub_date.get("Year", "N/A")
                    
                    # Abstract (truncate to ~400 chars)
                    abstract_data = article_data.get("Abstract", {})
                    abstract_texts = abstract_data.get("AbstractText", [])
                    if abstract_texts:
                        if isinstance(abstract_texts[0], str):
                            abstract = " ".join(abstract_texts)
                        else:
                            abstract = " ".join(str(t) for t in abstract_texts)
                    else:
                        abstract = "No abstract available"
                    if len(abstract) > 400:
                        abstract = abstract[:400] + "..."
                    
                    # PMID
                    pmid = medline.get("PMID", "")
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    
                    paper_str = (
                        f"{i}. {title}\n"
                        f"   Authors: {authors_str}\n"
                        f"   Journal: {journal} ({year})\n"
                        f"   Abstract: {abstract}\n"
                        f"   URL: {url}"
                    )
                    papers.append(paper_str)
                    
                except Exception:
                    continue
            
            if not papers:
                return f"Found {len(id_list)} papers but could not parse details."
            
            result = f"Found {len(papers)} papers in PubMed:\n\n"
            result += "\n\n".join(papers)
            return result
            
        except Exception as e:
            return f"PubMed search error: {str(e)}"


class SemanticScholarTool(BaseTool):
    """
    Search Semantic Scholar for academic papers across all disciplines.
    
    Uses the free Semantic Scholar API (no key required).
    Better coverage than PubMed for CS, physics, chemistry,
    and general research topics.
    """
    
    name: str = "search_semantic_scholar"
    description: str = (
        "Search Semantic Scholar (200M+ papers, all disciplines). "
        "Better coverage than PubMed for CS, physics, chemistry, "
        "general research."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Number of papers to return (1-100)"
            },
            "year": {
                "type": "string",
                "description": "Year range filter (e.g., '2020-2025')"
            }
        },
        "required": ["query"]
    }

    async def execute(
        self,
        query: str,
        limit: int = 10,
        year: Optional[str] = None
    ) -> str:
        """
        Execute Semantic Scholar search and return formatted results.
        
        Args:
            query: Search query string
            limit: Number of results to return (1-100)
            year: Optional year range filter (e.g., '2020-2025')
            
        Returns:
            Formatted string with paper details or error message
        """
        try:
            # Clamp limit
            limit = max(1, min(100, limit))
            
            # Build request
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": query,
                "limit": limit,
                "fields": "title,abstract,authors,year,citationCount,url,venue"
            }
            
            if year:
                params["year"] = year
            
            # Run blocking request in executor
            loop = asyncio.get_event_loop()
            
            def do_request():
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            
            data = await loop.run_in_executor(None, do_request)
            
            papers_data = data.get("data", [])
            
            if not papers_data:
                return f"No papers found in Semantic Scholar for query: '{query}'"
            
            # Format results
            papers = []
            for i, paper in enumerate(papers_data, 1):
                try:
                    title = paper.get("title", "No title")
                    
                    # Authors (first 3)
                    author_list = paper.get("authors", [])
                    authors = [a.get("name", "") for a in author_list[:3]]
                    authors_str = ", ".join(authors) if authors else "Unknown"
                    if len(author_list) > 3:
                        authors_str += " et al."
                    
                    year_val = paper.get("year", "N/A")
                    citations = paper.get("citationCount", 0)
                    venue = paper.get("venue", "Unknown venue") or "Unknown venue"
                    paper_url = paper.get("url", "No URL")
                    
                    # Abstract (truncate to ~400 chars)
                    abstract = paper.get("abstract", "No abstract available")
                    if abstract is None:
                        abstract = "No abstract available"
                    if len(abstract) > 400:
                        abstract = abstract[:400] + "..."
                    
                    paper_str = (
                        f"{i}. {title}\n"
                        f"   Authors: {authors_str}\n"
                        f"   Year: {year_val} | Citations: {citations}\n"
                        f"   Venue: {venue}\n"
                        f"   Abstract: {abstract}\n"
                        f"   URL: {paper_url}"
                    )
                    papers.append(paper_str)
                    
                except Exception:
                    continue
            
            if not papers:
                return f"Found {len(papers_data)} papers but could not parse details."
            
            result = f"Found {len(papers)} papers in Semantic Scholar:\n\n"
            result += "\n\n".join(papers)
            return result
            
        except requests.exceptions.Timeout:
            return "Semantic Scholar search error: Request timed out"
        except requests.exceptions.HTTPError as e:
            return f"Semantic Scholar search error: HTTP {e.response.status_code}"
        except Exception as e:
            return f"Semantic Scholar search error: {str(e)}"
