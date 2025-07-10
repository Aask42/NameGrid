from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, lightgrey, white, HexColor
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Register fonts
pdfmetrics.registerFont(TTFont('Dyslexie', 'Dyslexie_Bold_142436.ttf'))
pdfmetrics.registerFont(TTFont('FancyFont', 'fantasy-zone.ttf'))  # Use your font

CARD_WIDTH = 2.5 * inch   # Standard trading card width (MTG, Pokémon, etc.)
CARD_HEIGHT = 3.5 * inch  # Standard trading card height

# Standard margins and spacing constants for consistent MTG-style layout
MARGIN = 0.125 * inch      # Standard card margin (1/8 inch)
BORDER_WIDTH = 6           # Outer border thickness (thicker like MTG)
INNER_BORDER_WIDTH = 1     # Inner border thickness
TITLE_HEIGHT = 0.3 * inch  # Height reserved for title area
TYPE_LINE_HEIGHT = 0.2 * inch # Height for type line
ALT_BOX_HEIGHT = 0.15 * inch   # Height for alt text box
TEXT_BOX_HEIGHT = 1.1 * inch   # Height of main text box (increased for more space)
TEXT_PADDING = 0.08 * inch     # Padding inside text areas

def draw_trading_card_front(c, x, y, card, logo_path):
    # Outer black border with rounded corners (MTG-style thick border)
    c.setStrokeColor(black)
    c.setLineWidth(BORDER_WIDTH)
    c.setFillColor(HexColor('#F5F5DC'))  # Cream background like MTG
    c.roundRect(x, y, CARD_WIDTH, CARD_HEIGHT, radius=8, stroke=1, fill=1)
    
    # Removed inner decorative border for cleaner look
    
    # Content area calculations
    content_x = x + MARGIN
    content_y = y + MARGIN
    content_width = CARD_WIDTH - (2 * MARGIN)
    content_height = CARD_HEIGHT - (2 * MARGIN)

    # Title area with proper MTG-style background
    title_y = content_y + content_height - TITLE_HEIGHT
    c.setFillColor(HexColor('#E8E8E8'))
    c.setStrokeColor(black)
    c.setLineWidth(1)
    c.rect(content_x, title_y, content_width, TITLE_HEIGHT, fill=1, stroke=1)
    
    # Title text - centered and properly spaced
    c.setFont('Dyslexie', 16)
    c.setFillColor(black)
    title = card.get('title', '')
    title_text_y = title_y + (TITLE_HEIGHT / 2) - 6
    c.drawCentredString(content_x + content_width/2, title_text_y, title)
    
    # Remove detail text from title area - will be moved to bottom

    # Type line area
    type_y = title_y - TYPE_LINE_HEIGHT
    c.setFillColor(HexColor('#D3D3D3'))
    c.setStrokeColor(black)
    c.setLineWidth(1)
    c.rect(content_x, type_y, content_width, TYPE_LINE_HEIGHT, fill=1, stroke=1)
    
    # Type text - left aligned like MTG
    c.setFont('Dyslexie', 12)
    c.setFillColor(black)
    card_type = card.get('type', '')
    type_text_y = type_y + (TYPE_LINE_HEIGHT / 2) - 5
    c.drawString(content_x + TEXT_PADDING, type_text_y, card_type)

    # Main artwork area - properly centered and sized
    art_y = type_y - (content_height - TITLE_HEIGHT - TYPE_LINE_HEIGHT - ALT_BOX_HEIGHT - TEXT_BOX_HEIGHT)
    art_height = content_height - TITLE_HEIGHT - TYPE_LINE_HEIGHT - ALT_BOX_HEIGHT - TEXT_BOX_HEIGHT
    
    # Image with proper aspect ratio and centering
    img_path = card.get('img', logo_path)
    img_margin = TEXT_PADDING
    img_w = content_width - (2 * img_margin)
    img_h = art_height - (2 * img_margin)
    img_x = content_x + img_margin
    img_y = art_y + img_margin
    
    try:
        c.drawImage(img_path, img_x, img_y, img_w, img_h,
                   preserveAspectRatio=True, mask='auto')
    except:
        # Fallback: draw placeholder with border
        c.setFillColor(lightgrey)
        c.setStrokeColor(HexColor('#999999'))
        c.setLineWidth(1)
        c.rect(img_x, img_y, img_w, img_h, fill=1, stroke=1)
        c.setFillColor(HexColor('#666666'))
        c.setFont('Dyslexie', 10)
        c.drawCentredString(img_x + img_w/2, img_y + img_h/2, "IMAGE")

    # Alt text box between artwork and main text box
    alt_box_y = art_y - ALT_BOX_HEIGHT
    alt = card.get('alt', '')
    if alt:
        c.setFillColor(HexColor('#F0F0F0'))  # Light gray background
        c.setStrokeColor(black)
        c.setLineWidth(1)
        c.rect(content_x, alt_box_y, content_width, ALT_BOX_HEIGHT, fill=1, stroke=1)
        
        # Alt text - centered in its box
        c.setFont('Dyslexie', 9)
        c.setFillColor(HexColor('#333333'))
        alt_text_y = alt_box_y + (ALT_BOX_HEIGHT / 2) - 4
        c.drawCentredString(content_x + content_width/2, alt_text_y, alt)

    # Text box area - MTG style with proper spacing
    text_box_y = content_y
    c.setFillColor(HexColor('#FFFEF7'))  # Slightly off-white like MTG text boxes
    c.setStrokeColor(black)
    c.setLineWidth(1)
    c.rect(content_x, text_box_y, content_width, TEXT_BOX_HEIGHT, fill=1, stroke=1)
    
    # Action text with proper line spacing and margins using ReportLab's text wrapping
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    
    action = card.get('action', '')
    if action:
        # Determine optimal font size based on text length
        if len(action) > 200:
            font_size = 8
        elif len(action) > 100:
            font_size = 9
        else:
            font_size = 10
        
        # Create a custom paragraph style
        style = ParagraphStyle(
            'CardText',
            fontName='Dyslexie',
            fontSize=font_size,
            leading=font_size + 2,  # Line height
            alignment=TA_LEFT,
            leftIndent=0,
            rightIndent=0,
            spaceAfter=0,
            spaceBefore=0
        )
        
        # Create paragraph and calculate available space
        para = Paragraph(action, style)
        available_width = content_width - (2 * TEXT_PADDING)
        available_height = TEXT_BOX_HEIGHT - (2 * TEXT_PADDING)
        
        # Draw the paragraph higher in the text box
        para.wrapOn(c, available_width, available_height)
        # Position text higher by starting from the top of the text box
        text_start_y = text_box_y + TEXT_BOX_HEIGHT - TEXT_PADDING - para.height
        para.drawOn(c, content_x + TEXT_PADDING, text_start_y)

    # Detail text at bottom between text box and border (like MTG set info)
    detail = card.get('detail', '')
    if detail:
        c.setFont('Dyslexie', 6)  # Smaller font size
        c.setFillColor(HexColor('#666666'))
        # Position between text box and bottom border
        detail_y = content_y - TEXT_PADDING
        c.drawCentredString(content_x + content_width/2, detail_y, detail)

def draw_trading_card_back(c, x, y, card, logo_path):
    # Outer black border with rounded corners matching front
    c.setStrokeColor(black)
    c.setLineWidth(BORDER_WIDTH)
    c.setFillColor(HexColor('#1a1a2e'))  # Dark blue background
    c.roundRect(x, y, CARD_WIDTH, CARD_HEIGHT, radius=8, stroke=1, fill=1)
    
    # Removed inner decorative border for cleaner look
    
    # Content area
    content_x = x + MARGIN
    content_y = y + MARGIN
    content_width = CARD_WIDTH - (2 * MARGIN)
    content_height = CARD_HEIGHT - (2 * MARGIN)
    
    # Central logo area
    logo_size = 1.2 * inch
    logo_x = content_x + (content_width - logo_size) / 2
    logo_y = content_y + (content_height - logo_size) / 2
    
    try:
        c.drawImage(logo_path, logo_x, logo_y, logo_size, logo_size,
                   preserveAspectRatio=True, mask='auto')
    except:
        # Fallback: decorative text
        c.setFont('FancyFont', 24)
        c.setFillColor(HexColor('#4a4a6a'))
        c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT/2, "CARD")
        c.setFont('FancyFont', 16)
        c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT/2 - 30, "BACK")
    
    # Decorative corner elements
    corner_size = 0.15 * inch
    c.setFillColor(HexColor('#4a4a6a'))
    # Top corners
    c.circle(content_x + corner_size, content_y + content_height - corner_size, corner_size/3, fill=1)
    c.circle(content_x + content_width - corner_size, content_y + content_height - corner_size, corner_size/3, fill=1)
    # Bottom corners
    c.circle(content_x + corner_size, content_y + corner_size, corner_size/3, fill=1)
    c.circle(content_x + content_width - corner_size, content_y + corner_size, corner_size/3, fill=1)

def print_trading_cards(pdf_filename, cards, logo_path):
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    # Grid settings: 3x3 cards per page
    per_row = 3
    per_col = 3
    gap = 0.2 * inch
    left = 0.3 * inch
    top = 0.3 * inch
    # Layout helpers
    def get_xy(idx):
        row = idx // per_row
        col = idx % per_row
        x = left + col * (CARD_WIDTH + gap)
        y = letter[1] - top - (row + 1) * CARD_HEIGHT - row * gap
        return x, y

    # --- FRONT PAGES ---
    for p in range(0, len(cards), per_row * per_col):
        for idx, card in enumerate(cards[p:p+per_row*per_col]):
            x, y = get_xy(idx)
            draw_trading_card_front(c, x, y, card, logo_path)
        c.showPage()
    # --- BACK PAGES (in same order) ---
    for p in range(0, len(cards), per_row * per_col):
        for idx, card in enumerate(cards[p:p+per_row*per_col]):
            x, y = get_xy(idx)
            draw_trading_card_back(c, x, y, card, logo_path)
        c.showPage()
    c.save()

# ---- Example usage ----

sample_cards = [
    {
        "title": "Super Hacker",
        "type": "Attack",
        "img": "images/duald.png",
        "action": "Steal 2 creds.\nPlay only at night.",
        "alt": "Night hack",
        "detail": "Special event. DEF CON exclusive.",
    },
    {
        "title": "Trogdor",
        "type": "Burninator",
        "img": "images/trogdor.png",
        "action": "Opponent must be burninated",
        "alt": "BURN IT ALL",
        "detail": "Once per round.",
    },
    {
        "title": "(Bad)Aask",
        "type": "Hacker",
        "img": "images/amelia.png",
        "action": "Unexpected glitch in the system.\nSteal 1 cred from each opponent.",
        "alt": "Did I do that?",
        "detail": "When in the vicinity of technology",
    },
    {
        "title": "Sonicos",
        "type": "Alleged Hacker",
        "img": "images/sonicos.png",
        "action": "Tap to gain funding for your project, this remains tapped for the rest of DEF CON",
        "alt": "Black badge raffle??",
        "detail": "DT's best friend",
    },
    # ...more cards...
]

print_trading_cards("trading_cards.pdf", sample_cards * 5, "images/alien.png")
