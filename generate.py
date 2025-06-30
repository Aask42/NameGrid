from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, lightgrey, navy, Color
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import csv
from pathlib import Path
from typing import List, Dict, Union
from datetime import date

# Configure your nametag settings
inputFile = "nametags.csv" # NOTE: MUST be a CSV and columns MUST be: attendeeName,companyName,eventName
outputFile = "nametags.pdf" # Format should be: filename.pdf
logoFile = "logoold.png"
watermarkSize = 2.5 # Size in inches (2.5 is a good default)
watermarkAngle = 45 # Counter-clockwise rotation in degrees (45 is a good default)
watermarkOpacity = 10 # Opacity as percentage (10 is a good default)

# Register whatever fonts you want to use
# Here I'm using Dyslexie and a fancy font for the year
# NOTE: YOU MUST HAVE THESE FONTS INSTALLED OR AVAILABLE IN THE PATH 
# OR YOU MUST PROVIDE THE CORRECT PATHS TO THE FONT FILES

font_1 = "Dyslexie"
font_2 = "FancyFont"

pdfmetrics.registerFont(TTFont('Dyslexie', './Dyslexie_Bold_142436.ttf'))
pdfmetrics.registerFont(TTFont('FancyFont', './fantasy-zone.ttf'))  # Replace with the path to your fancy font

def draw_dotted_border(c, x, y, width, height, dot_size=1):
    c.setStrokeColor(lightgrey)
    c.setDash(dot_size, 2 * dot_size)
    c.rect(x, y, width, height, stroke=1, fill=0)

def draw_multiline_text(c, text, max_width, x, y, font, font_size):
    words = text.split()
    lines = []
    line = []
    line_height = font_size + 2  # Adjust the line height as needed
    for word in words:
        line.append(word)
        line_width = c.stringWidth(" ".join(line), font, font_size)
        if line_width > max_width:
            line.pop()
            lines.append(" ".join(line))
            line = [word]
    if line:
        lines.append(" ".join(line))
    
    # Center the whole block vertically
    total_height = len(lines) * line_height
    start_y = y - total_height / 2 + line_height / 2
    
    for line in lines:
        line_width = c.stringWidth(line, font, font_size)
        c.drawString(x + (max_width - line_width) / 2, start_y, line)
        start_y -= line_height

    return start_y  # Return the new y position after drawing the text

def draw_nametag(c, x, y, name, role, tagline, year, logo_path):
    # Draw the watermark logo
    logo_size = watermarkSize * inch  # Size of the watermark logo
    c.saveState()
    c.translate(x + 1.7 * inch, y + 1.7 * inch)
    c.rotate(watermarkAngle)
    c.setFillColor(Color(0, 0, 0, alpha=watermarkOpacity/100))  # Faded color
    c.drawImage(logo_path, -logo_size / 2, -logo_size / 2, logo_size, logo_size, mask='auto')
    c.restoreState()

    draw_dotted_border(c, x, y, 3.4 * inch, 3.4 * inch)
    c.setStrokeColor(black)
    c.setDash()

    # Set the font size for the name to be as large as possible and bold if available
    max_font_size = 22
    min_font_size = 16
    c.setFont(font_1, max_font_size)
    name_width = c.stringWidth(name, font_1, max_font_size)
    
    while name_width > (3.4 * inch - 10 * mm) and max_font_size > min_font_size:
        max_font_size -= 1
        c.setFont(font_1, max_font_size)
        name_width = c.stringWidth(name, font_1, max_font_size)
    
    text_y = y + 2.6 * inch
    if len(name) > 21:
        text_y = draw_multiline_text(c, name, 3.4 * inch - 10 * mm, x + 5 * mm, text_y, font_1, max_font_size)
    else:
        c.drawString(x + (3.4 * inch - name_width) / 2, text_y, name)
        text_y -= max_font_size + 2  # Adjust y position after drawing the name
    
    # Set the font size for the tagline to be slightly smaller
    max_font_size = 16
    min_font_size = 12
    c.setFont(font_1, max_font_size)
    tagline_width = c.stringWidth(tagline, font_1, max_font_size)
    
    while tagline_width > (3.4 * inch - 10 * mm) and max_font_size > min_font_size:
        max_font_size -= 1
        c.setFont(font_1, max_font_size)
        tagline_width = c.stringWidth(tagline, font_1, max_font_size)
    
    text_y -= 0.5 * inch
    c.drawString(x + (3.4 * inch - tagline_width) / 2, text_y, tagline)
    
    # Set the font size for the role
    c.setFont(font_1, 14)
    role_width = c.stringWidth(role, font_1, 14)
    
    text_y -= 0.5 * inch
    if len(role) > 21:
        text_y = draw_multiline_text(c, role, 3.4 * inch - 10 * mm, x + 5 * mm, text_y, font_1, 14)
    else:
        c.drawString(x + (3.4 * inch - role_width) / 2, text_y, role)
        text_y -= 14 + 2  # Adjust y position after drawing the role
    
    # Draw the year with a fancy style at the bottom left corner
    c.setFont(font_2, 14)
    year_width = c.stringWidth(year, font_2, 14)
    c.setFillColor(navy)
    c.drawString(x + 5 * mm, y + 5 * mm, year)
    c.setFillColor(black)  # Reset to default color for other elements
    
    # Draw the logo at the bottom right corner
    logo_size = 1 * inch  # Size of the logo
    c.drawImage(logo_path, x + 3.4 * inch - logo_size - 5 * mm, y + 5 * mm, logo_size, logo_size, mask='auto')

def load_nametags(csv_path: Union[str, Path]) -> List[Dict[str, str]]:
    nametag_names: List[Dict[str, str]] = []
    with Path(csv_path).expanduser().open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Optional sanity-check: make sure the needed columns exist
        expected = {"attendeeName", "companyName", "eventName"}
        if not expected.issubset(reader.fieldnames or []):
            missing = expected - set(reader.fieldnames or [])
            raise ValueError(f"CSV is missing columns: {', '.join(missing)}")
        for row in reader:
            nametag_names.append(
                {
                    "name": row["attendeeName"].strip(),
                    "Role": row["companyName"].strip(),
                    "Tagline_Mod": row["eventName"].strip(),
                }
            )
    return nametag_names

def create_nametags(pdf_filename, nametag_names, logo_path, year):
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    
    # Define the margins
    margin = 5 * mm
    nametag_width = 3.4 * inch
    nametag_height = 3.4 * inch
    
    # Calculate the x and y positions dynamically
    page_width, page_height = letter
    num_columns = 2
    num_rows = 3  # Adjusted for 6 nametags per page
    
    horizontal_gap = 0  # No gap between columns
    vertical_gap = 0  # No gap between rows
    
    x_positions = [margin + i * (nametag_width + horizontal_gap) for i in range(num_columns)]
    y_positions = [page_height - margin - (i + 1) * nametag_height for i in range(num_rows)]
    
    index = 0
    for name_info in nametag_names:
        name = name_info["name"]
        role = name_info["Role"]
        tagline = name_info["Tagline_Mod"]
        
        x = x_positions[index % num_columns]
        y = y_positions[(index // num_columns) % num_rows]
        
        draw_nametag(c, x, y, name, role, tagline, year, logo_path)
        
        index += 1
        if index % (num_columns * num_rows) == 0:
            c.showPage()

    # Add the last page if not complete
    if index % (num_columns * num_rows) != 0:
        c.showPage()

    c.save()

nametag_names = load_nametags(inputFile)

year = str(date.today().year)

create_nametags(outputFile, nametag_names, logoFile, year)