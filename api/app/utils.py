import re

def format_document_title(text: str) -> str:
    if not text:
        return "Unknown Source"
    
    text = re.sub(r'\.(pdf|docx|txt|html)$', '', text, flags=re.IGNORECASE)
    text = text.replace('_', ' ').replace('-', ' ')
    
    replacements = {
        r'\binstrucao\b': 'Instrução',
        r'\bresolucao\b': 'Resolução',
        r'\bacao\b': 'Ação',
        r'\b\( onselho\b': 'Conselho',
        r'\bconselho\b': 'Conselho',
        r'\breitoria\b': 'Reitoria',
        r'\bdecanato\b': 'Decanato',
        r'\bportaria\b': 'Portaria',
        r'/\s*N\.': 'N.',
        r'N[ºº]\s*/?\s*N\.?': 'N.',
        r'N[ºº]': 'N.',
        r'N\.': 'N.'
    }
    
    processed = text.lower()
    for pattern, replacement in replacements.items():
        processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)

    processed = re.sub(r'(Instrução|Portaria)\s+(Reitoria|Decanato)', r'\1 da \2', processed, flags=re.IGNORECASE)
    processed = re.sub(r'(Resolução)\s+(Conselho)', r'\1 do \2', processed, flags=re.IGNORECASE)

    words = processed.split()
    acronyms = ['CEPE', 'UNB', 'DGP', 'DEG', 'MEC', 'FUB', 'CPP', 'DIR', 'REI']
    exceptions = ['da', 'do', 'de', 'das', 'dos', 'e', 'em', 'no', 'na']
    
    final_words = []
    for i, word in enumerate(words):
        clean_word = word.upper().replace('.', '').replace(',', '')
        if clean_word in acronyms:
            final_words.append(word.upper())
        elif word.lower() in exceptions and i != 0:
            final_words.append(word.lower())
        else:
            final_words.append(word.capitalize())
            
    title = " ".join(final_words)
    numbers = re.findall(r'\d+', text)
    
    if len(numbers) >= 2:
        year = numbers[-1] if len(numbers[-1]) == 4 else numbers[0]
        num = numbers[0] if numbers[0] != year else (numbers[1] if len(numbers) > 1 else numbers[0])
        base_title = re.sub(r'\d+', '', title).replace('N.', '').replace('/', '').strip()
        base_title = " ".join(base_title.split())
        return f"{base_title} N. {num.zfill(4)}/{year}"
    
    return title