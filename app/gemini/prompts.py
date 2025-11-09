def create_analysis_prompt() -> str:
    base_prompt = """
    Analyze the receipt with meticulous attention to **main items**, **indented modifications**, **extras**, and **all associated charges**.  
    Your output must strictly follow the **JSON format** provided in the response schema. No deviations allowed.  

    OBJECTIVE: 
    - Detect every main item, its modifications, extras, and applicable taxes/service charges.
    - Correctly associate prices with each item/modification.  
    - Identify modifiers even if they appear on the same line, next line, or with special characters.  
    - Ignore unrelated text (e.g., store notes, discounts not associated with an item).
    """

    item_detection_rules = """
    CRITICAL ITEM DETECTION RULES:

    ...[same rules as previously defined]...

    EXAMPLES OF VARIOUS RECEIPT STRUCTURES:

    Example 1: Standard Food Order with Modifications
    2x *Burger Cheeseburger   U.P 12.00  Price 24.00
      - Extra Cheese            1.50
      - No Onions               0.00
    Tax 2.50
    Service 3.00
    Total 31.00

    Example 2: Beverage with Size and Temperature Modifiers
    1x *Cappuccino            5.00
      - Iced Jumbo             0.50
    1x *Latte                  4.50
      - Extra Shot             0.80
    Tax 1.20
    Total 11.00

    Example 3: Inline Multiple Modifications
    1x *Pizza Margherita      10.00
      - Thin Crust, Extra Cheese 1.50
      - No Olives               0.00
    Service 1.00
    Total 12.50

    Example 4: Quantity Modifier on Add-On
    1x *Chicken Wings          8.00
      - Extra Sauce x2         1.00
    Tax 0.80
    Total 9.80

    Example 5: Modifiers with Parentheses/Brackets
    1x *Latte                  4.50
      - Cold (Large)           0.50
      - Soy Milk [Extra]       0.30
    Total 5.30

    Example 6: Modifications Without Prices (assume 0)
    1x *Sandwich               6.00
      - Gluten Free Bread
      - No Mayo
    Tax 0.50
    Service 0.50
    Total 7.00

    Example 7: Mixed Food and Beverage
    1x *Burger                  12.00
      - Cheese                  1.50
    1x *Iced Tea                 3.00
      - Lemon                   0.00
    Tax 1.25
    Total 17.75

    Example 8: Discount Linked to Item
    1x *Pizza                  10.00
      - Extra Cheese            1.50
    Discount -1.00
    Tax 1.10
    Total 11.60

    Example 9: Misaligned Text or Multi-Column Style
    1x *Pasta                  U.P 9.00    Price 9.00
      - Extra Sauce                        0.50
      - Parmesan Cheese                     0.70
    Tax 1.10
    Service 0.90
    Total 12.20

    Example 10: Beverage Only with Multiple Modifiers
    1x *Frappuccino            5.00
      - Vanilla Syrup          0.50
      - Extra Whipped Cream    0.70
      - Large                  0.30
    Tax 0.90
    Service 0.50
    Total 7.90
    """

    return base_prompt + item_detection_rules
