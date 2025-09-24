def create_analysis_prompt() -> str:
    base_prompt = """
    Analyze the receipt with particular attention to indented modifications and their charges.
    Extract in this exact JSON format given from response schema:
    
    IMPORTANT: 
    - Do NOT perform any arithmetic, deduction, or recalculation.
    - Copy all values EXACTLY as shown in the receipt.
    - Treat every price, tax, and service charge as independent fields.
    - Do not merge, sum, or subtract values.
    """

    item_detection_rules = """
    CRITICAL ITEM DETECTION RULES:
    1. Main Item Format:
       - Lines starting with "1x *" are main items.
       - Extract their price directly from the "U.P" column as-is (no modification).
    
    2. Modification Format:
       - Lines starting with "-" or indented under main items are modifications.
       - Copy any price shown (even 0.00) from the same or next line.
    
    3. Price Association:
       - ANY price appearing below a main item should be included exactly as written.
       - Look at both "U.P" and "Price" columns, but do not recalculate.
    
    4. Special Cases:
       - For beverages, include temperature/size modifiers as written.
       - For food, include preparation modifiers and extras exactly.
    
    5. Taxes & Service Charges:
       - If listed, record them exactly as separate items.
       - Do not adjust or apply them to other prices.
    """
    return base_prompt + item_detection_rules
