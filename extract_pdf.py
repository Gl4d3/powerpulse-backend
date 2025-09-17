"""Extract text from the CSI research PDF."""

import PyPDF2
import sys

def extract_pdf_text(pdf_path):
    """Extract text from PDF file."""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            
            print(f"PDF has {len(reader.pages)} pages")
            
            # Extract text from all pages to get complete content
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                text += f"{page_text}\n"
            
            return text
            
    except Exception as e:
        print(f"Error reading PDF: {str(e)}")
        return None

if __name__ == "__main__":
    pdf_path = "attached_assets/csi-research.pdf"
    text = extract_pdf_text(pdf_path)
    
    if text:
        print("=== CSI Research PDF Content (First 5 Pages) ===")
        print(text[:3000])  # Show first 3000 characters
        print("\n[...content truncated...]")
        
        # Look for methodology sections
        print(f"\n=== Searching for Four Pillars Framework ===")
        
        # Search for pillar mentions
        pillars = ['effectiveness', 'efficiency', 'effort', 'empathy']
        for pillar in pillars:
            if pillar.lower() in text.lower():
                print(f"✅ {pillar.title()} pillar found in research")
                # Find context around the pillar
                pillar_pos = text.lower().find(pillar.lower())
                if pillar_pos != -1:
                    context_start = max(0, pillar_pos - 200)
                    context_end = min(len(text), pillar_pos + 500)
                    context = text[context_start:context_end]
                    print(f"   Context: ...{context.strip()}...\n")
            else:
                print(f"❌ {pillar.title()} pillar not explicitly mentioned")
        
        # Search for scoring methodology
        scoring_terms = ['0-10 scale', '0-100 scale', 'weighted average', 'scoring']
        print(f"\n=== Scoring Methodology Analysis ===")
        for term in scoring_terms:
            if term.lower() in text.lower():
                print(f"✅ '{term}' found in research")
            else:
                print(f"❌ '{term}' not found")
        
        # Save full text for detailed analysis
        with open('csi_research_full_text.txt', 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"\n✅ Full PDF text saved to 'csi_research_full_text.txt' for detailed analysis")
    else:
        print("Failed to extract PDF content")