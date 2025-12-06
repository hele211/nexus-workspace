"""
Test script for literature search tools.

Run from project root:
    source spoon-env/bin/activate
    python -m backend.test_literature_tools
"""

import asyncio
import sys


async def test_pubmed():
    """Test PubMedSearchTool with a sample query."""
    print("\n" + "=" * 60)
    print("=== PubMed Test ===")
    print("=" * 60)
    
    try:
        from backend.tools.literature_tools import PubMedSearchTool
        
        pubmed = PubMedSearchTool()
        print(f"Tool name: {pubmed.name}")
        print(f"Query: 'CRISPR gene editing' (max_results=3)")
        print("-" * 60)
        
        result = await pubmed.execute("CRISPR gene editing", max_results=3)
        print(result)
        
        # Check result
        if "Found" in result and "papers" in result:
            return True, "Papers retrieved successfully"
        elif "error" in result.lower():
            return False, result
        elif "No papers found" in result:
            return False, "No papers found (query may be too specific)"
        else:
            return True, "Response received"
            
    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:
        return False, f"Exception: {e}"


async def test_semantic_scholar():
    """Test SemanticScholarTool with a sample query."""
    print("\n" + "=" * 60)
    print("=== Semantic Scholar Test ===")
    print("=" * 60)
    
    try:
        from backend.tools.literature_tools import SemanticScholarTool
        
        semantic = SemanticScholarTool()
        print(f"Tool name: {semantic.name}")
        print(f"Query: 'machine learning protein folding' (limit=3)")
        print("-" * 60)
        
        result = await semantic.execute("machine learning protein folding", limit=3)
        print(result)
        
        # Check result
        if "Found" in result and "papers" in result:
            return True, "Papers retrieved successfully"
        elif "error" in result.lower():
            return False, result
        elif "No papers found" in result:
            return False, "No papers found (query may be too specific)"
        else:
            return True, "Response received"
            
    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:
        return False, f"Exception: {e}"


async def main():
    """Run all tool tests."""
    print("\n" + "=" * 60)
    print("  LITERATURE TOOLS TEST")
    print("=" * 60)
    
    results = []
    
    # Test PubMed
    pubmed_ok, pubmed_msg = await test_pubmed()
    results.append(("PubMed", pubmed_ok, pubmed_msg))
    
    # Test Semantic Scholar
    semantic_ok, semantic_msg = await test_semantic_scholar()
    results.append(("Semantic Scholar", semantic_ok, semantic_msg))
    
    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed, msg in results:
        if passed:
            print(f"✅ {name} tool working: {msg}")
        else:
            print(f"❌ {name} failed: {msg}")
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All literature tools verified - ready for LiteratureAgent!")
        return 0
    else:
        print("⚠️  Some tools had issues - check errors above")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
