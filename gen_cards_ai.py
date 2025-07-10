import os
import requests
from PIL import Image
from io import BytesIO
import base64
import numpy as np
import yaml
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, lightgrey, white, HexColor
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Import the existing card generation constants
from gen_cards import (
    CARD_WIDTH, CARD_HEIGHT, MARGIN, BORDER_WIDTH, INNER_BORDER_WIDTH,
    TITLE_HEIGHT, ALT_BOX_HEIGHT, TEXT_BOX_HEIGHT, TEXT_PADDING
)

# Override constants for AI cards
TYPE_LINE_HEIGHT = 0.14 * inch  # 30% smaller than original (0.2 * 0.7 = 0.14)
TITLE_HEIGHT = 0.3 * inch - 2  # Make title box 2 pixels smaller than original
TEXT_BOX_HEIGHT = 1.1 * inch + 24  # Make text box 24 pixels taller than original (18 + 6)

# Register fonts (same as original)
pdfmetrics.registerFont(TTFont('ELEGANT', 'ELEGANT TYPEWRITER Regular.ttf'))
pdfmetrics.registerFont(TTFont('FancyFont', 'fantasy-zone.ttf'))

class OpenAIImageGenerator:
    """
    Class to handle OpenAI DALL-E image generation for trading card backgrounds
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the OpenAI image generator
        
        Args:
            api_key (str): OpenAI API key. If None, will try to get from environment
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.base_url = "https://api.openai.com/v1/images/generations"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_card_background(self, prompt, card_title="", card_type="", size="1792x1024", quality="hd"):
        """
        Generate a background image for a trading card using OpenAI DALL-E with optimal settings
        
        Args:
            prompt (str): Description of the image to generate
            card_title (str): Title of the card (used to enhance prompt)
            card_type (str): Type of card (used to enhance prompt)
            size (str): Image size - "1792x1024" (landscape) is optimal for 5:3 ratio
            quality (str): Image quality - "hd" for better crispness
        
        Returns:
            PIL.Image: Generated image processed to perfect 5:3 aspect ratio
        """
        # Enhance the prompt with card context and quality specifications
        enhanced_prompt = self._enhance_prompt(prompt, card_title, card_type)
        
        payload = {
            "model": "dall-e-3",
            "prompt": enhanced_prompt,
            "n": 1,
            "size": size,
            "quality": quality,
            "response_format": "url"
        }
        
        try:
            print(f"  Attempting to generate with prompt: {enhanced_prompt[:100]}...")
            print(f"  Payload size: {len(str(payload))} characters")
            print(f"  Model: {payload['model']}, Size: {payload['size']}, Quality: {payload['quality']}")
            
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            
            if response.status_code != 200:
                print(f"  API Error {response.status_code}: {response.text}")
                print(f"  Request headers: {self.headers}")
                print(f"  Full prompt length: {len(enhanced_prompt)} characters")
                if len(enhanced_prompt) > 4000:
                    print(f"  WARNING: Prompt may be too long ({len(enhanced_prompt)} chars)")
                return None
                
            result = response.json()
            image_url = result['data'][0]['url']
            
            # Download and process the image
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            
            # Load image and convert to 5:3 aspect ratio
            image = Image.open(BytesIO(image_response.content))
            processed_image = self._process_image_for_card(image)
            
            return processed_image
            
        except requests.exceptions.RequestException as e:
            print(f"  Network error generating image: {e}")
            return None
        except Exception as e:
            print(f"  Unexpected error: {e}")
            return None
    
    def _enhance_prompt(self, base_prompt, card_title, card_type):
        """
        Enhance the base prompt with card-specific context for more coherent backgrounds
        
        Args:
            base_prompt (str): Original prompt
            card_title (str): Card title
            card_type (str): Card type
        
        Returns:
            str: Enhanced prompt optimized for coherent, edge-to-edge backgrounds
        """
        enhancements = []
        
        if card_title:
            enhancements.append(f"themed around '{card_title}'")
        
        if card_type:
            # More specific and coherent type themes
            type_themes = {
                "Attack": "dynamic battlefield environment with energy effects and motion blur",
                "Defense": "fortified stronghold with protective barriers and defensive structures",
                "Hacker": "high-tech cyberpunk environment with neon lighting, servers, and digital interfaces",
                "Burninator": "medieval countryside with wooden structures, rolling hills, and dramatic fire effects",
                "Special": "mystical realm with magical energy, ethereal lighting, and otherworldly atmosphere",
                "Alleged Hacker": "Shows a script kiddie room with questionable tech and shadowy elements",
                "Space-Human": "futuristic space station interior with advanced technology and cosmic views"
            }
            if card_type in type_themes:
                enhancements.append(type_themes[card_type])
        
        # Simplified styling for concise prompts
        style_additions = [
            "trading card background",
            "edge to edge",
            "no characters"
        ]
        
        # Build a concise enhanced prompt
        enhanced_prompt = f"{base_prompt}"
        
        if enhancements:
            enhanced_prompt += f", {', '.join(enhancements[:1])}"  # Only use first enhancement
        
        enhanced_prompt += f", {', '.join(style_additions)}"
        
        # Limit prompt to 400 characters to avoid API issues while keeping effectiveness
        if len(enhanced_prompt) > 400:
            enhanced_prompt = enhanced_prompt[:397] + "..."
            print(f"  Prompt truncated to 400 characters")
        
        return enhanced_prompt
    
    def _process_image_for_card(self, image):
        """
        Process the generated image to fit card background requirements with improved quality
        
        Args:
            image (PIL.Image): Original generated image
        
        Returns:
            PIL.Image: Processed image with perfect 5:3 aspect ratio and crisp quality
        """
        # Calculate 5:3 aspect ratio dimensions
        target_ratio = 5/3
        width, height = image.size
        current_ratio = width / height
        
        # Use smart cropping that preserves the most important content (center-weighted)
        if current_ratio > target_ratio:
            # Image is too wide, crop width but keep center content
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            image = image.crop((left, 0, left + new_width, height))
        elif current_ratio < target_ratio:
            # Image is too tall, crop height but keep center content
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            image = image.crop((0, top, width, top + new_height))
        
        # Use higher resolution for better crispness (400 DPI equivalent)
        # 5:3 ratio at high quality - ensures backgrounds are crisp and fill to edges
        target_width = 1500  # Increased from 1000 for better quality
        target_height = 900  # Increased from 600 for better quality
        
        # Use high-quality resampling with sharpening
        image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Apply subtle sharpening to enhance crispness
        from PIL import ImageFilter, ImageEnhance
        
        # Enhance sharpness slightly
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)  # 10% sharpness boost
        
        # Enhance contrast slightly for better definition
        contrast_enhancer = ImageEnhance.Contrast(image)
        image = contrast_enhancer.enhance(1.05)  # 5% contrast boost
        
        return image
    
    def create_background_with_subject_composite(self, image_path, card_title="", card_type=""):
        """
        Create a themed background and composite the original subject on top - PRESERVES ORIGINAL SUBJECT
        
        Args:
            image_path (str): Path to the existing image
            card_title (str): Title of the card
            card_type (str): Type of card
        
        Returns:
            PIL.Image: Composite image with original subject preserved on themed background
        """
        try:
            # Load and prepare the original image
            original_image = Image.open(image_path)
            original_image = original_image.convert('RGBA')
            
            # Generate background prompt directly (avoiding circular import)
            card_data = {
                'title': card_title,
                'type': card_type,
                'action': '',  # We'll focus on title and type for background
                'alt': '',
                'detail': ''
            }
            
            # Generate background prompt using the function defined later in this file
            background_prompt = self._generate_themed_background_prompt(card_title, card_type)
            
            # Generate the background image (without any subject)
            print(f"  Generating themed background for {card_title}")
            background_image = self.generate_card_background(
                background_prompt,
                card_title,
                card_type
            )
            
            if not background_image:
                print(f"  Failed to generate background, using processed original")
                return self._process_existing_image(image_path)
            
            # Now composite the original subject onto the background
            # Use the original image directly (no background removal)
            subject_image = original_image
            
            # Calculate optimal size and position for the subject
            bg_width, bg_height = background_image.size
            subj_width, subj_height = subject_image.size
            
            # Scale subject to fit nicely (about 60-70% of background height)
            target_subject_height = int(bg_height * 0.65)
            scale_factor = target_subject_height / subj_height
            new_subj_width = int(subj_width * scale_factor)
            new_subj_height = int(subj_height * scale_factor)
            
            # Resize subject with high quality
            resized_subject = subject_image.resize((new_subj_width, new_subj_height), Image.Resampling.LANCZOS)
            
            # Position subject (slightly off-center for more dynamic composition)
            paste_x = int(bg_width * 0.4) - (new_subj_width // 2)  # Slightly left of center
            paste_y = int(bg_height * 0.5) - (new_subj_height // 2)  # Vertically centered
            
            # Ensure subject stays within bounds
            paste_x = max(0, min(paste_x, bg_width - new_subj_width))
            paste_y = max(0, min(paste_y, bg_height - new_subj_height))
            
            # Create final composite
            final_image = background_image.copy()
            
            # Paste subject with alpha blending
            if resized_subject.mode == 'RGBA':
                final_image.paste(resized_subject, (paste_x, paste_y), resized_subject)
            else:
                final_image.paste(resized_subject, (paste_x, paste_y))
            
            print(f"  Successfully composited subject onto themed background")
            return final_image
            
        except Exception as e:
            print(f"Error creating background composite: {e}")
            # Fallback to original processing
            return self._process_existing_image(image_path)

    def extend_image_outward(self, image_path, card_title="", card_type=""):
        """
        DEPRECATED: Use create_background_with_subject_composite instead for better subject preservation
        """
        print(f"  Using composite method for better subject preservation")
        return self.create_background_with_subject_composite(image_path, card_title, card_type)

    def create_composite_background(self, base_prompt, existing_image_path=None, card_title="", card_type=""):
        """
        Create a composite background that incorporates existing artwork if provided
        
        Args:
            base_prompt (str): Base description for the background
            existing_image_path (str): Path to existing image to incorporate (optional)
            card_title (str): Title of the card
            card_type (str): Type of card
        
        Returns:
            PIL.Image: Composite background image
        """
        if existing_image_path and os.path.exists(existing_image_path):
            # Try to use the composite method, but fallback gracefully if API fails
            print(f"  Attempting to create composite background for existing image")
            extended_image = self.create_background_with_subject_composite(existing_image_path, card_title, card_type)
            
            if extended_image:
                return extended_image
            else:
                # Fallback to just processing the existing image with enhanced quality
                print(f"  API unavailable, using enhanced processing of original image")
                return self._process_existing_image(existing_image_path)
        else:
            # No existing image, try to generate background but fallback gracefully
            print(f"  No existing image, attempting background generation")
            enhanced_prompt = f"Simple {card_type} background"  # Very simple prompt
            generated_bg = self.generate_card_background(enhanced_prompt, card_title, card_type)
            
            if generated_bg:
                return generated_bg
            else:
                # Create a simple colored background as ultimate fallback
                print(f"  Creating simple fallback background")
                return self._create_simple_background(card_type)
    
    def _process_existing_image(self, image_path):
        """
        Process an existing image to fit card requirements
        
        Args:
            image_path (str): Path to the existing image
        
        Returns:
            PIL.Image: Processed image
        """
        try:
            image = Image.open(image_path)
            return self._process_image_for_card(image)
        except Exception as e:
            print(f"Error processing existing image: {e}")
            return None

    def _create_simple_background(self, card_type):
        """
        Create a simple colored background as fallback when API is unavailable
        
        Args:
            card_type (str): Type of card to determine background color
        
        Returns:
            PIL.Image: Simple colored background in 5:3 ratio
        """
        try:
            # Define colors based on card type
            type_colors = {
                "Attack": "#8B0000",      # Dark red
                "Defense": "#000080",     # Navy blue
                "Hacker": "#006400",      # Dark green
                "Burninator": "#FF4500",  # Orange red
                "Special": "#4B0082",     # Indigo
                "Alleged Hacker": "#2F4F4F",  # Dark slate gray
                "Space-Human": "#191970"  # Midnight blue
            }
            
            # Get color for card type, default to dark gray
            bg_color = type_colors.get(card_type, "#2F2F2F")
            
            # Create image with 5:3 ratio at high quality
            width, height = 1500, 900
            background = Image.new('RGB', (width, height), bg_color)
            
            print(f"  Created simple {bg_color} background for {card_type}")
            return background
            
        except Exception as e:
            print(f"Error creating simple background: {e}")
            # Ultimate fallback - dark gray
            return Image.new('RGB', (1500, 900), "#2F2F2F")

    def remove_background(self, image_path):
        """
        Remove background from an image using simple color-based removal
        
        Args:
            image_path (str): Path to the image
        
        Returns:
            PIL.Image: Image with background removed (transparent)
        """
        try:
            image = Image.open(image_path)
            image = image.convert('RGBA')
            
            # Convert to numpy array for processing
            data = np.array(image)
            
            # Get the corner pixels to determine background color
            corners = [
                data[0, 0],      # top-left
                data[0, -1],     # top-right
                data[-1, 0],     # bottom-left
                data[-1, -1]     # bottom-right
            ]
            
            # Find the most common corner color (likely background)
            from collections import Counter
            corner_colors = [tuple(corner[:3]) for corner in corners]  # RGB only
            most_common_bg = Counter(corner_colors).most_common(1)[0][0]
            
            # Create mask for background removal
            # Calculate color distance from background color
            bg_r, bg_g, bg_b = most_common_bg
            
            # Calculate distance from background color
            r_diff = np.abs(data[:, :, 0].astype(int) - bg_r)
            g_diff = np.abs(data[:, :, 1].astype(int) - bg_g)
            b_diff = np.abs(data[:, :, 2].astype(int) - bg_b)
            
            # Total color distance
            color_distance = r_diff + g_diff + b_diff
            
            # Threshold for background removal (adjust as needed)
            threshold = 50  # Lower = more aggressive removal
            
            # Set alpha channel based on color distance
            data[:, :, 3] = np.where(color_distance < threshold, 0, data[:, :, 3])
            
            # Convert back to PIL Image
            result_image = Image.fromarray(data, 'RGBA')
            
            return result_image
            
        except Exception as e:
            print(f"Error removing background: {e}")
            # Return original image if background removal fails
            try:
                return Image.open(image_path).convert('RGBA')
            except:
                return None

    def modify_existing_artwork(self, original_image_path, modification_prompt, strength=0.7):
        """
        Modify existing artwork using OpenAI's image editing capabilities
        
        Args:
            original_image_path (str): Path to the original image
            modification_prompt (str): Description of how to modify the image
            strength (float): How much to modify (0.0 to 1.0)
        
        Returns:
            PIL.Image: Modified image
        """
        try:
            # Load and prepare the original image
            with open(original_image_path, 'rb') as f:
                original_image = Image.open(f)
                
            # Convert to RGBA if not already
            if original_image.mode != 'RGBA':
                original_image = original_image.convert('RGBA')
            
            # Resize to supported size (1024x1024 max for edits)
            original_image = original_image.resize((1024, 1024), Image.Resampling.LANCZOS)
            
            # Save to bytes for API
            img_byte_arr = BytesIO()
            original_image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Create a simple mask (you might want to make this more sophisticated)
            mask = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
            mask_byte_arr = BytesIO()
            mask.save(mask_byte_arr, format='PNG')
            mask_byte_arr = mask_byte_arr.getvalue()
            
            # Prepare the API request
            files = {
                'image': ('image.png', img_byte_arr, 'image/png'),
                'mask': ('mask.png', mask_byte_arr, 'image/png'),
                'prompt': (None, modification_prompt),
                'n': (None, '1'),
                'size': (None, '1024x1024')
            }
            
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = requests.post(
                "https://api.openai.com/v1/images/edits",
                headers=headers,
                files=files
            )
            response.raise_for_status()
            
            result = response.json()
            image_url = result['data'][0]['url']
            
            # Download the modified image
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            
            modified_image = Image.open(BytesIO(image_response.content))
            processed_image = self._process_image_for_card(modified_image)
            
            return processed_image
            
        except Exception as e:
            print(f"Error modifying artwork: {e}")
            return None

    def _generate_themed_background_prompt(self, card_title, card_type):
        """
        Generate a themed background prompt based on card title and type
        
        Args:
            card_title (str): Title of the card
            card_type (str): Type of card
        
        Returns:
            str: Background prompt
        """
        # Simplified version of generate_auto_prompt for backgrounds only
        environment_elements = []
        lighting_mood = []
        specific_details = []
        
        # Extract context from title
        title_lower = card_title.lower()
        if 'hacker' in title_lower or 'cyber' in title_lower:
            environment_elements.append("underground cyberpunk hacker den")
            specific_details.extend(["multiple glowing monitors", "tangled cables", "server racks", "neon accent lighting"])
            lighting_mood.append("dramatic blue and green neon lighting")
        elif 'dragon' in title_lower or 'fire' in title_lower:
            environment_elements.append("epic fantasy dragon's lair")
            specific_details.extend(["ancient stone architecture", "treasure piles", "mystical runes", "volcanic elements"])
            lighting_mood.append("warm orange and red fire glow")
        elif 'trogdor' in title_lower:
            environment_elements.append("medieval countryside village")
            specific_details.extend(["thatched roof cottages", "rolling green hills", "wooden fences", "peasant dwellings"])
            lighting_mood.append("dramatic sunset lighting with fire glow")
        elif 'phantom' in title_lower or 'ghost' in title_lower:
            environment_elements.append("haunted ethereal realm")
            specific_details.extend(["swirling mist", "ghostly apparitions", "ancient ruins", "supernatural energy"])
            lighting_mood.append("eerie moonlight with ethereal blue glow")
        elif 'space' in title_lower or 'alien' in title_lower:
            environment_elements.append("futuristic space station interior")
            specific_details.extend(["holographic displays", "sleek metal surfaces", "starfield views", "advanced technology"])
            lighting_mood.append("cool blue and white sci-fi lighting")
        
        # Add type-based environmental context
        type_environments = {
            "Attack": {
                "environment": "dynamic combat arena",
                "details": ["energy weapons effects", "battle debris", "motion blur"],
                "lighting": "dramatic action lighting with sparks"
            },
            "Defense": {
                "environment": "fortified defensive position",
                "details": ["protective barriers", "shield generators", "defensive structures"],
                "lighting": "steady, protective blue lighting"
            },
            "Hacker": {
                "environment": "high-tech hacker laboratory",
                "details": ["multiple screens", "server farms", "cable management", "RGB lighting"],
                "lighting": "cool blue and green tech lighting"
            },
            "Burninator": {
                "environment": "medieval countryside landscape",
                "details": ["wooden buildings", "rural elements", "fire effects", "peasant architecture"],
                "lighting": "warm fire glow against twilight sky"
            },
            "Special": {
                "environment": "mystical magical realm",
                "details": ["magical energy effects", "otherworldly architecture", "floating elements"],
                "lighting": "ethereal magical glow"
            },
            "Alleged Hacker": {
                "environment": "mysterious tech environment",
                "details": ["shadowy elements", "question mark motifs", "uncertain tech"],
                "lighting": "mysterious shadowy lighting with tech glows"
            },
            "Space-Human": {
                "environment": "advanced space facility",
                "details": ["futuristic architecture", "alien technology", "cosmic elements"],
                "lighting": "advanced sci-fi lighting with cosmic effects"
            }
        }
        
        if card_type in type_environments:
            type_info = type_environments[card_type]
            environment_elements.append(type_info["environment"])
            specific_details.extend(type_info["details"])
            lighting_mood.append(type_info["lighting"])
        
        # Default fallback
        if not environment_elements:
            environment_elements.append("detailed fantasy adventure environment")
            specific_details.extend(["atmospheric elements", "rich textures"])
            lighting_mood.append("cinematic lighting")
        
        # Construct prompt
        main_environment = environment_elements[0] if environment_elements else "detailed environment"
        
        prompt_parts = [
            f"Background: {main_environment}",
            f"Details: {', '.join(specific_details[:2])}",  # Reduced details
            f"Lighting: {lighting_mood[0] if lighting_mood else 'ambient'}"  # Single lighting
        ]
        
        return ". ".join(prompt_parts)

def draw_trading_card_front_ai(c, x, y, card, logo_path, card_index=0):
    """
    Modified version of draw_trading_card_front with 10% smaller text for AI cards
    """
    # Outer black border with rounded corners (MTG-style thick border)
    c.setStrokeColor(black)
    c.setLineWidth(BORDER_WIDTH)
    c.setFillColor(HexColor('#F5F5DC'))  # Cream background like MTG
    c.roundRect(x, y, CARD_WIDTH, CARD_HEIGHT, radius=8, stroke=1, fill=1)
    
    # Content area calculations
    content_x = x + MARGIN
    content_y = y + MARGIN
    content_width = CARD_WIDTH - (2 * MARGIN)
    content_height = CARD_HEIGHT - (2 * MARGIN)

    # Calculate positions for text boxes first (needed for image positioning)
    title_y = content_y + content_height - TITLE_HEIGHT
    title_expansion = -1  # pixels to shrink on each side (4px thinner on each side)
    expanded_title_x = content_x - title_expansion
    expanded_title_width = content_width + (2 * title_expansion)
    type_y = title_y - TYPE_LINE_HEIGHT - 1  # Move down 1 pixel for tighter spacing
    expanded_type_x = content_x - title_expansion
    expanded_type_width = content_width + (2 * title_expansion)
    
    # Main artwork area - DRAWN FIRST so text boxes appear on top
    # Calculate the full area available for the image
    text_box_top = content_y + TEXT_BOX_HEIGHT
    if card.get('alt', ''):
        # If there's alt text, image goes from type line to alt box
        img_bottom = text_box_top + ALT_BOX_HEIGHT
    else:
        # If no alt text, image goes from type line to text box
        img_bottom = text_box_top
    
    # Expand image area to go under the type box and use very thin vertical gaps
    base_img_w = content_width  # Original width
    # Extend image height to go under the type box (add TYPE_LINE_HEIGHT + spacing)
    base_img_h = (type_y - img_bottom) + TYPE_LINE_HEIGHT + 4  # Extend up under type box
    
    # Make the picture 15% bigger
    scale_factor = 1.05
    scaled_img_w = base_img_w * scale_factor
    scaled_img_h = base_img_h * scale_factor
    
    # Very thin vertical gaps between picture and border
    vertical_gap = 0.25  # Very thin gap on each side
    
    # Calculate image dimensions with very thin vertical gaps and 15% scaling
    img_w = scaled_img_w - (2 * vertical_gap)  # Reduce width by gaps on both sides
    img_h = scaled_img_h  # Use extended and scaled height
    # Center the larger image
    img_x = content_x + vertical_gap - ((scaled_img_w - base_img_w) / 2)  # Center horizontally
    img_y = img_bottom - ((scaled_img_h - base_img_h) / 2) - 4 + 6  # Center vertically, moved up 6px more (now +2)
    
    # Image with proper aspect ratio and vertical gaps (no drop shadow)
    img_path = card.get('img', logo_path)
    
    try:
        c.drawImage(img_path, img_x, img_y, img_w, img_h,
                   preserveAspectRatio=True, mask='auto')
    except:
        # Fallback: draw placeholder with border (also with shadow)
        c.setFillColor(lightgrey)
        c.setStrokeColor(HexColor('#999999'))
        c.setLineWidth(1)
        c.rect(img_x, img_y, img_w, img_h, fill=1, stroke=1)
        c.setFillColor(HexColor('#666666'))
        c.setFont('ELEGANT', 9)  # 10% smaller (was 10, now 9)
        c.drawCentredString(img_x + img_w/2, img_y + img_h/2, "IMAGE")

    # NOW DRAW TEXT BOXES ON TOP OF THE IMAGE
    
    # Title area with proper MTG-style background - EXPANDED to overlap image
    c.setFillColor(HexColor('#E8E8E8'))
    c.setStrokeColor(black)
    c.setLineWidth(1)
    c.rect(expanded_title_x, title_y, expanded_title_width, TITLE_HEIGHT, fill=1, stroke=1)
    
    # Title text - 10% smaller (was 16, now 14.4 ≈ 14), left aligned
    c.setFont('ELEGANT', 14)
    c.setFillColor(black)
    title = card.get('title', '')
    title_text_y = title_y + (TITLE_HEIGHT / 2) - 5  # Adjusted for smaller font
    # Left align text in the expanded title box with same padding as type text
    title_text_x = expanded_title_x + TEXT_PADDING
    c.drawString(title_text_x, title_text_y, title)

    # Type line area - REMOVED: Type text now goes in alt box with "BURN IT ALL"
    # (Commented out the separate type box)

    # Combined type/alt text box - contains both "Burninator" (left) and "BURN IT ALL" (right)
    alt_box_y = img_bottom - 4  # Move down 6 pixels from previous position (back to -4)
    alt_box_height = ALT_BOX_HEIGHT + 4  # Make alt box 4 pixels taller
    alt = card.get('alt', '')
    card_type = card.get('type', '')
    
    # Always draw the box if there's either alt text or card type
    if alt or card_type:
        c.setFillColor(HexColor('#F0F0F0'))  # Light gray background
        c.setStrokeColor(black)
        c.setLineWidth(1)
        c.rect(content_x, alt_box_y, content_width, alt_box_height, fill=1, stroke=1)
        
        c.setFont('ELEGANT', 8)  # Font for both texts
        c.setFillColor(HexColor('#333333'))
        text_y = alt_box_y + (alt_box_height / 2) - 3  # Adjusted for smaller font and taller box
        
        # Left-aligned card type (Burninator)
        if card_type:
            type_text_x = content_x + TEXT_PADDING
            c.drawString(type_text_x, text_y, card_type)
        
        # Right-aligned alt text (BURN IT ALL)
        if alt:
            alt_text_x = content_x + content_width - TEXT_PADDING
            c.drawRightString(alt_text_x, text_y, alt)

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
        # Determine optimal font size based on text length - 10% smaller
        if len(action) > 200:
            font_size = 7  # was 8, now 7.2 ≈ 7
        elif len(action) > 100:
            font_size = 8  # was 9, now 8.1 ≈ 8
        else:
            font_size = 9  # was 10, now 9
        
        # Create a custom paragraph style
        style = ParagraphStyle(
            'CardText',
            fontName='ELEGANT',
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

    # Detail text at bottom between text box and border - 10% smaller (was 6, now 5.4 ≈ 5)
    # Move up 1 pixel and right align, plus add auto-generated card number on left
    detail = card.get('detail', '')
    detail_y = content_y - TEXT_PADDING + 1  # Move up 1 pixel
    
    # Dynamic card number starting at 0
    card_number = f"#{card_index:03d}"
    
    c.setFont('ELEGANT', 5)
    c.setFillColor(HexColor('#666666'))
    
    # Left-aligned card number
    c.drawString(content_x + TEXT_PADDING, detail_y, card_number)
    
    # Right-aligned detail text
    if detail:
        detail_x = content_x + content_width - TEXT_PADDING
        c.drawRightString(detail_x, detail_y, detail)

def draw_trading_card_back_ai(c, x, y, card, logo_path):
    """
    Modified version of draw_trading_card_back for AI cards (same as original since no text changes needed)
    """
    # Outer black border with rounded corners matching front
    c.setStrokeColor(black)
    c.setLineWidth(BORDER_WIDTH)
    c.setFillColor(HexColor('#1a1a2e'))  # Dark blue background
    c.roundRect(x, y, CARD_WIDTH, CARD_HEIGHT, radius=8, stroke=1, fill=1)
    
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
        # Fallback: decorative text - 10% smaller fonts
        c.setFont('FancyFont', 22)  # was 24, now 21.6 ≈ 22
        c.setFillColor(HexColor('#4a4a6a'))
        c.drawCentredString(x + CARD_WIDTH/2, y + CARD_HEIGHT/2, "CARD")
        c.setFont('FancyFont', 14)  # was 16, now 14.4 ≈ 14
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

def print_trading_cards_ai(pdf_filename, cards, logo_path):
    """
    Modified version of print_trading_cards using AI-specific card drawing functions
    """
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    # Grid settings: 3x3 cards per page with minimal gaps for easy cutting
    per_row = 3
    per_col = 3
    gap = 0.05 * inch  # Minimal gap for cutting guides
    left = 0.15 * inch  # Smaller left margin
    top = 0.15 * inch   # Smaller top margin
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
            card_index = p + idx  # Calculate global card index starting from 0
            draw_trading_card_front_ai(c, x, y, card, logo_path, card_index)
        c.showPage()
    # --- BACK PAGES (in same order) ---
    for p in range(0, len(cards), per_row * per_col):
        for idx, card in enumerate(cards[p:p+per_row*per_col]):
            x, y = get_xy(idx)
            draw_trading_card_back_ai(c, x, y, card, logo_path)
        c.showPage()
    c.save()

def save_generated_image(image, filename):
    """
    Save a generated image to the images directory
    
    Args:
        image (PIL.Image): Image to save
        filename (str): Filename (without path)
    
    Returns:
        str: Full path to saved image
    """
    if not os.path.exists('images'):
        os.makedirs('images')
    
    filepath = os.path.join('images', filename)
    image.save(filepath, 'PNG', quality=95)
    return filepath

def generate_auto_prompt(card):
    """
    Generate an automatic prompt based on card content that creates coherent, edge-to-edge backgrounds
    
    Args:
        card (dict): Card data
    
    Returns:
        str: Generated prompt for contextually coherent background
    """
    title = card.get('title', '')
    card_type = card.get('type', '')
    action = card.get('action', '')
    alt = card.get('alt', '')
    detail = card.get('detail', '')
    
    # Analyze all card content to create a comprehensive, coherent background
    environment_elements = []
    lighting_mood = []
    specific_details = []
    
    # Extract context from title with more specific environments
    title_lower = title.lower()
    if 'hacker' in title_lower or 'cyber' in title_lower:
        environment_elements.append("underground cyberpunk hacker den")
        specific_details.extend(["multiple glowing monitors", "tangled cables", "server racks", "neon accent lighting"])
        lighting_mood.append("dramatic blue and green neon lighting")
    elif 'dragon' in title_lower or 'fire' in title_lower:
        environment_elements.append("epic fantasy dragon's lair")
        specific_details.extend(["ancient stone architecture", "treasure piles", "mystical runes", "volcanic elements"])
        lighting_mood.append("warm orange and red fire glow")
    elif 'trogdor' in title_lower:
        environment_elements.append("medieval countryside village")
        specific_details.extend(["thatched roof cottages", "rolling green hills", "wooden fences", "peasant dwellings"])
        lighting_mood.append("dramatic sunset lighting with fire glow")
    elif 'phantom' in title_lower or 'ghost' in title_lower:
        environment_elements.append("haunted ethereal realm")
        specific_details.extend(["swirling mist", "ghostly apparitions", "ancient ruins", "supernatural energy"])
        lighting_mood.append("eerie moonlight with ethereal blue glow")
    elif 'space' in title_lower or 'alien' in title_lower:
        environment_elements.append("futuristic space station interior")
        specific_details.extend(["holographic displays", "sleek metal surfaces", "starfield views", "advanced technology"])
        lighting_mood.append("cool blue and white sci-fi lighting")
    
    # Extract context from action text for additional environmental details
    action_lower = action.lower()
    if 'night' in action_lower:
        lighting_mood.append("nighttime atmosphere with ambient lighting")
        specific_details.append("city lights in background")
    elif 'space' in action_lower:
        environment_elements.append("outer space environment")
        specific_details.extend(["distant planets", "starfield", "spacecraft elements"])
    elif 'funding' in action_lower or 'project' in action_lower:
        environment_elements.append("modern tech conference hall")
        specific_details.extend(["presentation screens", "conference crowds", "tech displays"])
    elif 'burninate' in action_lower:
        specific_details.extend(["flames and smoke effects", "burning structures", "dramatic fire"])
        lighting_mood.append("intense fire lighting")
    elif 'glitch' in action_lower or 'system' in action_lower:
        specific_details.extend(["digital glitch effects", "code streams", "matrix-style elements"])
    
    # Extract context from alt and detail text
    if alt:
        alt_lower = alt.lower()
        if 'hack' in alt_lower:
            specific_details.extend(["hacking tools", "command terminals"])
        elif 'burn' in alt_lower:
            specific_details.extend(["destruction aftermath", "smoke and ash"])
        elif 'leaving' in alt_lower:
            specific_details.extend(["departure vehicles", "travel elements"])
    
    if detail:
        detail_lower = detail.lower()
        if 'def con' in detail_lower:
            environment_elements.append("DEF CON conference environment")
            specific_details.extend(["hacker conference atmosphere", "tech vendor booths"])
        elif 'exclusive' in detail_lower:
            specific_details.extend(["premium materials", "luxury elements"])
        elif 'space' in detail_lower:
            specific_details.extend(["space station corridors", "zero gravity elements"])
    
    # Add type-based environmental context with more specificity
    type_environments = {
        "Attack": {
            "environment": "dynamic combat arena",
            "details": ["energy weapons effects", "battle debris", "motion blur"],
            "lighting": "dramatic action lighting with sparks"
        },
        "Defense": {
            "environment": "fortified defensive position",
            "details": ["protective barriers", "shield generators", "defensive structures"],
            "lighting": "steady, protective blue lighting"
        },
        "Hacker": {
            "environment": "high-tech hacker laboratory",
            "details": ["multiple screens", "server farms", "cable management", "RGB lighting"],
            "lighting": "cool blue and green tech lighting"
        },
        "Burninator": {
            "environment": "medieval countryside landscape",
            "details": ["wooden buildings", "rural elements", "fire effects", "peasant architecture"],
            "lighting": "warm fire glow against twilight sky"
        },
        "Special": {
            "environment": "mystical magical realm",
            "details": ["magical energy effects", "otherworldly architecture", "floating elements"],
            "lighting": "ethereal magical glow"
        },
        "Alleged Hacker": {
            "environment": "mysterious tech environment",
            "details": ["shadowy elements", "question mark motifs", "uncertain tech"],
            "lighting": "mysterious shadowy lighting with tech glows"
        },
        "Space-Human": {
            "environment": "advanced space facility",
            "details": ["futuristic architecture", "alien technology", "cosmic elements"],
            "lighting": "advanced sci-fi lighting with cosmic effects"
        }
    }
    
    if card_type in type_environments:
        type_info = type_environments[card_type]
        environment_elements.append(type_info["environment"])
        specific_details.extend(type_info["details"])
        lighting_mood.append(type_info["lighting"])
    
    # Default fallback for rich environment
    if not environment_elements:
        environment_elements.append("detailed fantasy adventure environment")
        specific_details.extend(["atmospheric elements", "rich textures", "environmental storytelling"])
        lighting_mood.append("cinematic lighting")
    
    # Construct a coherent, comprehensive prompt
    main_environment = environment_elements[0] if environment_elements else "detailed environment"
    
    prompt_parts = [
        f"Background: {main_environment}",
        f"Details: {', '.join(specific_details[:3])}",  # Reduced to 3 details
        f"Lighting: {', '.join(lighting_mood[:1])}",  # Reduced to 1 lighting element
        "Edge-to-edge, no borders"
    ]
    
    base_prompt = ". ".join(prompt_parts)
    
    return base_prompt

def generate_ai_cards(cards_data, logo_path="images/alien.png", output_filename="ai_trading_cards.pdf", auto_generate_backgrounds=True, disable_ai=False):
    """
    Generate trading cards with AI-generated backgrounds for every card
    
    Args:
        cards_data (list): List of card dictionaries
        logo_path (str): Path to logo image
        output_filename (str): Output PDF filename
        auto_generate_backgrounds (bool): Whether to generate backgrounds for all cards
    """
    # Initialize the AI image generator (skip if disabled)
    if disable_ai:
        print("AI generation disabled - using original images only")
        ai_generator = None
    else:
        try:
            ai_generator = OpenAIImageGenerator()
        except ValueError as e:
            print(f"Error initializing AI generator: {e}")
            print("Continuing without AI generation...")
            ai_generator = None
    
    # Process each card and generate images
    processed_cards = []
    
    for i, card in enumerate(cards_data):
        print(f"Processing card {i+1}/{len(cards_data)}: {card.get('title', 'Untitled')}")
        
        card_copy = card.copy()
        
        # Skip AI processing if disabled or no generator available
        if disable_ai or ai_generator is None:
            processed_cards.append(card)
            continue
        
        # Determine what kind of background to generate
        if 'ai_prompt' in card:
            # Explicit AI prompt provided
            base_prompt = card['ai_prompt']
        elif auto_generate_backgrounds:
            # Auto-generate prompt based on card content
            base_prompt = generate_auto_prompt(card)
        else:
            # No AI processing, use original card
            processed_cards.append(card)
            continue
        
        # Check if there's an existing image to incorporate
        existing_image = card.get('img', None)
        
        # Generate composite background
        if 'modify_prompt' in card and existing_image:
            # Specific modification requested
            modified_image = ai_generator.modify_existing_artwork(
                existing_image,
                card['modify_prompt']
            )
            
            if modified_image:
                image_filename = f"modified_card_{i+1}_{card.get('title', 'untitled').lower().replace(' ', '_').replace('(', '').replace(')', '')}.png"
                image_path = save_generated_image(modified_image, image_filename)
                card_copy['img'] = image_path
                print(f"  Modified artwork saved as: {image_path}")
            else:
                print(f"  Failed to modify artwork, using original image")
        else:
            # Generate composite background (with or without existing image)
            composite_image = ai_generator.create_composite_background(
                base_prompt,
                existing_image,
                card.get('title', ''),
                card.get('type', '')
            )
            
            if composite_image:
                image_filename = f"ai_card_{i+1}_{card.get('title', 'untitled').lower().replace(' ', '_').replace('(', '').replace(')', '')}.png"
                image_path = save_generated_image(composite_image, image_filename)
                card_copy['img'] = image_path
                print(f"  Generated background saved as: {image_path}")
            else:
                print(f"  Failed to generate background, using original image")
        
        processed_cards.append(card_copy)
    
    # Generate the PDF with processed cards using AI-specific functions
    print(f"\nGenerating PDF: {output_filename}")
    print_trading_cards_ai(output_filename, processed_cards, logo_path)
    print(f"AI-enhanced trading cards saved as: {output_filename}")

def load_cards_from_yaml(yaml_file="cards.yaml"):
    """
    Load card data from a YAML file
    
    Args:
        yaml_file (str): Path to the YAML file containing card data
    
    Returns:
        list: List of card dictionaries
    """
    try:
        with open(yaml_file, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            return data.get('cards', [])
    except FileNotFoundError:
        print(f"Error: YAML file '{yaml_file}' not found.")
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return []
    except Exception as e:
        print(f"Error loading cards from YAML: {e}")
        return []

# Example usage with AI prompts
if __name__ == "__main__":
    # Load cards from YAML file
    cards_data = load_cards_from_yaml("cards.yaml")
    
    if cards_data:
        print(f"Loaded {len(cards_data)} cards from YAML file")
        # Generate cards with AI backgrounds (set disable_ai=True to skip AI generation)
        generate_ai_cards(cards_data, "images/alien.png", "ai_enhanced_cards.pdf", disable_ai=False)
    else:
        print("No cards loaded. Please check the YAML file.")