def create_analysis_prompt() -> str:
    base_prompt = """
    Analyze the receipt with particular attention to indented modifications and their charges.
    Extract in this exact JSON format given from response schema:
    """

    item_detection_rules = """
    CRITICAL ITEM DETECTION RULES:
    1. Main Item Format:
       - Lines starting with "1x *" are main items
       - Extract their base price from the "U.P" column
       - Tax and service charges are 2 different prices, do not duplicate them.

    2. Modification Format:
       - Lines starting with "-" or indented under main items are modifications
       - Look for additional prices on the same or next line
       - Common formats:
         * "- Cold"
         * "- Cold (Jumbo)"
         * "- thin"

    3. Price Association:
       - ANY price appearing below a main item should be considered
       - Check both "U.P" and "Price" columns for modification costs
       - Include modifications even if price is 0.00

    4. Special Cases:
       - For beverages, look for temperature/size modifiers
       - For food, look for preparation modifiers and extras
    """
    return base_prompt + item_detection_rules
