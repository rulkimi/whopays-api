def create_analysis_prompt() -> str:
	base_prompt = """
	Analyze the receipt with particular attention to indented modifications and their charges.
	Extract in this exact JSON format given from response schema:
	
	IMPORTANT:
	- Do NOT perform any arithmetic, deduction, or recalculation.
	- Copy all values EXACTLY as shown in the receipt.
	- Treat every price, tax, and service charge as independent fields.
	- Do not merge, sum, or subtract values.
	- If the bill separates the items, do NOT combine them—follow exactly what the bill wrote, including values as displayed.
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

	6. Item Separation:
	   - If the bill separates any items, modifiers, or charges into multiple lines, DO NOT combine or group them. List each one individually as it appears.
	"""

	quantity_price_rules = """
	CRITICAL QUANTITY AND PRICE INTERPRETATION RULES:
	1. Quantity Field:
	   - The "quantity" field represents the NUMBER OF PEOPLE SHARING the item.
	   - If an item shows "x4" or "4x", the quantity is 4 (people sharing).
	   - This is NOT the number of individual units purchased.

	2. Unit Price Field:
	   - The "unit_price" field represents the TOTAL PRICE for the entire item.
	   - If a receipt shows "Chicken Rice x4" with price "54.99", then:
	     * quantity = 4 (people sharing)
	     * unit_price = 54.99 (total price for all 4 people)
	   - Do NOT multiply unit_price by quantity.

	3. Examples:
	   - Receipt shows: "Nasi Lemak x2" with price "25.00"
	     * quantity = 2, unit_price = 25.00
	   - Receipt shows: "Coffee x3" with price "15.50"
	     * quantity = 3, unit_price = 15.50
	   - Receipt shows: "Pizza x6" with price "89.99"
	     * quantity = 6, unit_price = 89.99

	4. Price Extraction:
	   - Always extract the final displayed price as the unit_price.
	   - Do not perform any calculations or multiplications.
	   - The price shown on the receipt is the total price for that item.
	"""
	return base_prompt + item_detection_rules + quantity_price_rules
