#!/usr/bin/env python3
"""
Timeline.js CSV to JSON Converter

This script converts CSV files to Timeline.js JSON format with full feature support.
Supports all documented and undocumented Timeline.js features including:
- Title slides with media and backgrounds
- Events with rich media, backgrounds, and advanced options
- Eras for background time periods
- Media type detection and validation
- Date/time parsing with multiple formats
- Error handling and validation

Usage:
    python csv_to_timeline.py input.csv [output.json] [--scale human|cosmological] [--validate]

Author: Timeline.js CSV Converter
Version: 1.0
"""

import csv
import json
import sys
import argparse
import re
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urlparse
import os

class TimelineError(Exception):
    """Custom exception for Timeline processing errors"""
    pass

class MediaTypeDetector:
    """Detects media types from URLs using patterns similar to Timeline.js"""
    
    MEDIA_PATTERNS = [
        {'pattern': r'youtube|youtu\.be', 'type': 'youtube', 'name': 'YouTube Video'},
        {'pattern': r'vimeo\.com', 'type': 'vimeo', 'name': 'Vimeo Video'},
        {'pattern': r'twitter\.com|x\.com', 'type': 'twitter', 'name': 'Twitter Post'},
        {'pattern': r'instagram\.com.*\/p\/', 'type': 'instagram', 'name': 'Instagram Post'},
        {'pattern': r'flickr\.com\/photos', 'type': 'flickr', 'name': 'Flickr Photo'},
        {'pattern': r'soundcloud\.com', 'type': 'soundcloud', 'name': 'SoundCloud Audio'},
        {'pattern': r'spotify\.com', 'type': 'spotify', 'name': 'Spotify Audio'},
        {'pattern': r'google\.com\/maps', 'type': 'googlemaps', 'name': 'Google Maps'},
        {'pattern': r'wikipedia\.org', 'type': 'wikipedia', 'name': 'Wikipedia Article'},
        {'pattern': r'commons\.wikimedia\.org.*\.(jpg|jpeg|png|gif|svg|webp)', 'type': 'wikipedia-image', 'name': 'Wikipedia Image'},
        {'pattern': r'dailymotion\.com|dai\.ly', 'type': 'dailymotion', 'name': 'DailyMotion Video'},
        {'pattern': r'vine\.co', 'type': 'vine', 'name': 'Vine Video'},
        {'pattern': r'documentcloud\.org', 'type': 'documentcloud', 'name': 'Document Cloud'},
        {'pattern': r'drive\.google\.com', 'type': 'googledocs', 'name': 'Google Drive'},
        {'pattern': r'imgur\.com', 'type': 'imgur', 'name': 'Imgur Image'},
        {'pattern': r'wistia\.com|wi\.st', 'type': 'wistia', 'name': 'Wistia Video'},
        {'pattern': r'\.(jpg|jpeg|png|gif|svg|webp)(\?.*)?$', 'type': 'image', 'name': 'Image'},
        {'pattern': r'\.(mp4|webm|avi|mov)(\?.*)?$', 'type': 'video', 'name': 'Video File'},
        {'pattern': r'\.(mp3|wav|ogg|m4a)(\?.*)?$', 'type': 'audio', 'name': 'Audio File'},
        {'pattern': r'\.(pdf)(\?.*)?$', 'type': 'pdf', 'name': 'PDF Document'},
    ]
    
    @classmethod
    def detect_type(cls, url: str) -> Dict[str, str]:
        """Detect media type from URL"""
        if not url:
            return {'type': 'unknown', 'name': 'Unknown'}
            
        url_lower = url.lower()
        for media in cls.MEDIA_PATTERNS:
            if re.search(media['pattern'], url_lower, re.IGNORECASE):
                return {'type': media['type'], 'name': media['name']}
                
        return {'type': 'link', 'name': 'Web Link'}

class DateParser:
    """Handles parsing of various date formats for Timeline.js"""
    
    DATE_FORMATS = [
        '%Y-%m-%d',      # 2023-06-15
        '%Y-%m',         # 2023-06
        '%Y',            # 2023
        '%m/%d/%Y',      # 06/15/2023
        '%d/%m/%Y',      # 15/06/2023
        '%B %d, %Y',     # June 15, 2023
        '%d %B %Y',      # 15 June 2023
        '%b %d, %Y',     # Jun 15, 2023
        '%d %b %Y',      # 15 Jun 2023
    ]
    
    TIME_FORMATS = [
        '%H:%M:%S',      # 14:30:45
        '%H:%M',         # 14:30
        '%I:%M:%S %p',   # 02:30:45 PM
        '%I:%M %p',      # 02:30 PM
    ]
    
    @classmethod
    def parse_date(cls, date_str: str, time_str: str = '') -> Optional[Dict[str, int]]:
        """Parse date string into Timeline.js date object"""
        if not date_str:
            return None
            
        date_str = date_str.strip()
        time_str = time_str.strip() if time_str else ''
        
        # Try to parse the date
        date_obj = None
        for fmt in cls.DATE_FORMATS:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        
        if not date_obj:
            # Try to extract year from string
            year_match = re.search(r'(\d{4})', date_str)
            if year_match:
                try:
                    year = int(year_match.group(1))
                    return {'year': year}
                except ValueError:
                    pass
            raise TimelineError(f"Could not parse date: {date_str}")
        
        # Build date object
        result = {
            'year': date_obj.year,
            'month': date_obj.month,
            'day': date_obj.day
        }
        
        # Parse time if provided
        if time_str:
            time_obj = None
            for fmt in cls.TIME_FORMATS:
                try:
                    time_obj = datetime.strptime(time_str, fmt)
                    break
                except ValueError:
                    continue
            
            if time_obj:
                result['hour'] = time_obj.hour
                result['minute'] = time_obj.minute
                if time_obj.second:
                    result['second'] = time_obj.second
        
        return result

class TimelineConverter:
    """Main converter class for CSV to Timeline.js JSON"""
    
    REQUIRED_COLUMNS = ['Type', 'Headline', 'Start Date']
    
    CSV_COLUMNS = [
        'Type', 'Headline', 'Text', 'Start Date', 'End Date', 'Display Date', 
        'Group', 'Media URL', 'Media Caption', 'Media Credit', 'Media Alt', 
        'Media Link', 'Media Link Target', 'Background Color', 'Background Image', 
        'Unique ID', 'Start Time', 'End Time'
    ]
    
    def __init__(self, scale: str = 'human', validate: bool = True):
        self.scale = scale
        self.validate = validate
        self.errors = []
        self.warnings = []
        
    def convert_csv_to_json(self, csv_file_path: str) -> Dict[str, Any]:
        """Convert CSV file to Timeline.js JSON format"""
        timeline_data = {
            'scale': self.scale,
            'events': [],
            'eras': []
        }
        
        # Read and process CSV
        try:
            with open(csv_file_path, 'r', encoding='utf-8', newline='') as csvfile:
                # Try to detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                
                delimiter = ','
                if sample.count('\t') > sample.count(','):
                    delimiter = '\t'
                elif sample.count(';') > sample.count(','):
                    delimiter = ';'
                
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                
                # Validate headers
                if not self._validate_headers(reader.fieldnames):
                    raise TimelineError("CSV headers validation failed")
                
                # Process each row
                for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                    try:
                        self._process_row(row, row_num, timeline_data)
                    except Exception as e:
                        error_msg = f"Row {row_num}: {str(e)}"
                        self.errors.append(error_msg)
                        if self.validate:
                            continue  # Skip invalid rows in validation mode
                        
        except FileNotFoundError:
            raise TimelineError(f"CSV file not found: {csv_file_path}")
        except Exception as e:
            raise TimelineError(f"Error reading CSV file: {str(e)}")
        
        # Validation
        if self.validate and self.errors:
            raise TimelineError(f"Validation failed with {len(self.errors)} errors:\n" + "\n".join(self.errors))
        
        # Final validation
        if not timeline_data['events'] and not timeline_data.get('title'):
            raise TimelineError("Timeline must have at least one event or a title slide")
            
        return timeline_data
    
    def _validate_headers(self, headers: List[str]) -> bool:
        """Validate CSV headers"""
        if not headers:
            self.errors.append("CSV file appears to be empty or invalid")
            return False
            
        missing_required = []
        for required in self.REQUIRED_COLUMNS:
            if required not in headers:
                missing_required.append(required)
        
        if missing_required:
            self.errors.append(f"Missing required columns: {', '.join(missing_required)}")
            return False
            
        return True
    
    def _process_row(self, row: Dict[str, str], row_num: int, timeline_data: Dict[str, Any]):
        """Process a single CSV row"""
        # Clean row data
        row = {k: v.strip() if v else '' for k, v in row.items()}
        
        row_type = row.get('Type', '').lower()
        headline = row.get('Headline', '')
        start_date = row.get('Start Date', '')
        
        # Validate required fields
        if not headline:
            raise ValueError("Headline is required")
        
        if row_type == 'title':
            timeline_data['title'] = self._build_title_slide(row, row_num)
        elif row_type == 'event':
            if not start_date:
                raise ValueError("Start Date is required for events")
            timeline_data['events'].append(self._build_event(row, row_num))
        elif row_type == 'era':
            end_date = row.get('End Date', '')
            if not start_date or not end_date:
                raise ValueError("Start Date and End Date are required for eras")
            timeline_data['eras'].append(self._build_era(row, row_num))
        else:
            raise ValueError(f"Invalid Type: {row_type}. Must be 'title', 'event', or 'era'")
    
    def _build_title_slide(self, row: Dict[str, str], row_num: int) -> Dict[str, Any]:
        """Build title slide object"""
        title = {
            'text': {
                'headline': row.get('Headline', ''),
                'text': row.get('Text', '')
            }
        }
        
        # Add media
        media = self._build_media_object(row, row_num)
        if media:
            title['media'] = media
        
        # Add background
        background = self._build_background_object(row)
        if background:
            title['background'] = background
            
        # Add unique ID
        unique_id = row.get('Unique ID', '')
        if unique_id:
            title['unique_id'] = unique_id
            
        return title
    
    def _build_event(self, row: Dict[str, str], row_num: int) -> Dict[str, Any]:
        """Build event object"""
        event = {
            'text': {
                'headline': row.get('Headline', ''),
                'text': row.get('Text', '')
            }
        }
        
        # Parse dates
        try:
            start_date = DateParser.parse_date(row.get('Start Date', ''), row.get('Start Time', ''))
            if start_date:
                event['start_date'] = start_date
        except Exception as e:
            raise ValueError(f"Invalid Start Date: {str(e)}")
        
        end_date_str = row.get('End Date', '')
        if end_date_str:
            try:
                end_date = DateParser.parse_date(end_date_str, row.get('End Time', ''))
                if end_date:
                    event['end_date'] = end_date
            except Exception as e:
                self.warnings.append(f"Row {row_num}: Invalid End Date: {str(e)}")
        
        # Add optional fields
        display_date = row.get('Display Date', '')
        if display_date:
            event['display_date'] = display_date
            
        group = row.get('Group', '')
        if group:
            event['group'] = group
            
        unique_id = row.get('Unique ID', '')
        if unique_id:
            event['unique_id'] = unique_id
        
        # Add media
        media = self._build_media_object(row, row_num)
        if media:
            event['media'] = media
        
        # Add background
        background = self._build_background_object(row)
        if background:
            event['background'] = background
            
        return event
    
    def _build_era(self, row: Dict[str, str], row_num: int) -> Dict[str, Any]:
        """Build era object"""
        era = {
            'text': {
                'headline': row.get('Headline', ''),
                'text': row.get('Text', '')
            }
        }
        
        # Parse dates (required for eras)
        try:
            start_date = DateParser.parse_date(row.get('Start Date', ''))
            end_date = DateParser.parse_date(row.get('End Date', ''))
            
            if not start_date or not end_date:
                raise ValueError("Both Start Date and End Date are required for eras")
                
            era['start_date'] = start_date
            era['end_date'] = end_date
            
        except Exception as e:
            raise ValueError(f"Invalid dates: {str(e)}")
        
        # Add unique ID
        unique_id = row.get('Unique ID', '')
        if unique_id:
            era['unique_id'] = unique_id
            
        return era
    
    def _build_media_object(self, row: Dict[str, str], row_num: int) -> Optional[Dict[str, str]]:
        """Build media object from row data"""
        media_url = row.get('Media URL', '')
        if not media_url:
            return None
        
        # Validate URL format
        if self.validate and not self._is_valid_url(media_url):
            self.warnings.append(f"Row {row_num}: Invalid Media URL format: {media_url}")
        
        media = {'url': media_url}
        
        # Add optional media fields
        caption = row.get('Media Caption', '')
        if caption:
            media['caption'] = caption
            
        credit = row.get('Media Credit', '')
        if credit:
            media['credit'] = credit
            
        alt = row.get('Media Alt', '')
        if alt:
            media['alt'] = alt
            
        link = row.get('Media Link', '')
        if link:
            if self.validate and not self._is_valid_url(link):
                self.warnings.append(f"Row {row_num}: Invalid Media Link URL format: {link}")
            media['link'] = link
            
        link_target = row.get('Media Link Target', '')
        if link_target:
            media['link_target'] = link_target
            
        return media
    
    def _build_background_object(self, row: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Build background object from row data"""
        bg_color = row.get('Background Color', '')
        bg_image = row.get('Background Image', '')
        
        if not bg_color and not bg_image:
            return None
        
        background = {}
        
        if bg_color:
            # Validate color format (hex, rgb, color names)
            if self.validate and not self._is_valid_color(bg_color):
                self.warnings.append(f"Invalid Background Color format: {bg_color}")
            background['color'] = bg_color
            
        if bg_image:
            if self.validate and not self._is_valid_url(bg_image):
                self.warnings.append(f"Invalid Background Image URL format: {bg_image}")
            background['url'] = bg_image
            
        return background
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _is_valid_color(self, color: str) -> bool:
        """Validate color format (hex, rgb, or named colors)"""
        # Hex colors
        if re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', color):
            return True
            
        # RGB colors
        if re.match(r'^rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)$', color):
            return True
            
        # RGBA colors
        if re.match(r'^rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[01](\.\d+)?\s*\)$', color):
            return True
            
        # Named colors (basic list)
        named_colors = [
            'red', 'green', 'blue', 'white', 'black', 'yellow', 'orange', 'purple', 
            'pink', 'gray', 'grey', 'brown', 'cyan', 'magenta', 'lime', 'navy', 
            'teal', 'silver', 'gold', 'violet', 'indigo', 'turquoise'
        ]
        
        return color.lower() in named_colors

def create_template_csv(output_path: str = 'timeline_template.csv'):
    """Create a template CSV file with example data"""
    
    template_data = [
        {
            'Type': 'title',
            'Headline': 'The Space Race',
            'Text': 'Key milestones in the competition between the United States and Soviet Union to achieve superior spaceflight capability.',
            'Start Date': '',
            'End Date': '',
            'Display Date': '',
            'Group': '',
            'Media URL': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Apollo_11_Saturn_V_lifting_off_on_July_16%2C_1969.jpg/800px-Apollo_11_Saturn_V_lifting_off_on_July_16%2C_1969.jpg',
            'Media Caption': 'Apollo 11 Saturn V rocket launches',
            'Media Credit': 'NASA',
            'Media Alt': 'Apollo 11 launch',
            'Media Link': 'https://nasa.gov',
            'Media Link Target': '_blank',
            'Background Color': '#000080',
            'Background Image': 'https://example.com/space-bg.jpg',
            'Unique ID': 'title-slide',
            'Start Time': '',
            'End Time': ''
        },
        {
            'Type': 'event',
            'Headline': 'Sputnik 1 Launched',
            'Text': 'The Soviet Union successfully launches the first artificial satellite, marking the beginning of the Space Age.',
            'Start Date': '1957-10-04',
            'End Date': '',
            'Display Date': '',
            'Group': 'Soviet Achievements',
            'Media URL': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Sputnik_asm.jpg/400px-Sputnik_asm.jpg',
            'Media Caption': 'Sputnik 1 satellite',
            'Media Credit': 'Wikipedia',
            'Media Alt': 'First artificial satellite',
            'Media Link': 'https://en.wikipedia.org/wiki/Sputnik_1',
            'Media Link Target': '_blank',
            'Background Color': '#8B0000',
            'Background Image': '',
            'Unique ID': 'sputnik-launch',
            'Start Time': '',
            'End Time': ''
        },
        {
            'Type': 'era',
            'Headline': 'Cold War Space Competition',
            'Text': 'Period of intense space exploration rivalry between the US and Soviet Union.',
            'Start Date': '1957-10-04',
            'End Date': '1975-07-17',
            'Display Date': '',
            'Group': 'Space Race Era',
            'Media URL': '',
            'Media Caption': '',
            'Media Credit': '',
            'Media Alt': '',
            'Media Link': '',
            'Media Link Target': '',
            'Background Color': '#E6E6FA',
            'Background Image': '',
            'Unique ID': 'cold-war-era',
            'Start Time': '',
            'End Time': ''
        }
    ]
    
    with open(output_path, 'w', encoding='utf-8', newline='') as csvfile:
        if template_data:
            fieldnames = template_data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(template_data)
    
    print(f"Template CSV created: {output_path}")
    return output_path

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(
        description='Convert CSV files to Timeline.js JSON format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python csv_to_timeline.py timeline.csv
  python csv_to_timeline.py timeline.csv output.json --scale cosmological
  python csv_to_timeline.py timeline.csv --validate --scale human
  python csv_to_timeline.py --template  # Create template CSV

CSV Format:
  Required columns: Type, Headline, Start Date
  Type values: title, event, era
  
  All columns:
  Type, Headline, Text, Start Date, End Date, Display Date, Group,
  Media URL, Media Caption, Media Credit, Media Alt, Media Link,
  Media Link Target, Background Color, Background Image, Unique ID,
  Start Time, End Time
        """
    )
    
    parser.add_argument('input_csv', nargs='?', help='Input CSV file path')
    parser.add_argument('output_json', nargs='?', help='Output JSON file path (optional)')
    parser.add_argument('--scale', choices=['human', 'cosmological'], default='human',
                      help='Timeline scale (default: human)')
    parser.add_argument('--validate', action='store_true',
                      help='Enable strict validation')
    parser.add_argument('--template', action='store_true',
                      help='Create a template CSV file')
    parser.add_argument('--stats', action='store_true',
                      help='Show conversion statistics')
    
    args = parser.parse_args()
    
    # Create template
    if args.template:
        template_path = create_template_csv()
        print("Template created successfully!")
        print(f"Edit {template_path} and run: python {sys.argv[0]} {template_path}")
        return
    
    # Validate arguments
    if not args.input_csv:
        parser.error("Input CSV file is required (or use --template to create one)")
    
    if not os.path.exists(args.input_csv):
        print(f"Error: Input file '{args.input_csv}' not found")
        return 1
    
    # Determine output file
    if args.output_json:
        output_file = args.output_json
    else:
        base_name = os.path.splitext(args.input_csv)[0]
        output_file = f"{base_name}_timeline.json"
    
    try:
        # Convert CSV to JSON
        converter = TimelineConverter(scale=args.scale, validate=args.validate)
        
        print(f"Converting {args.input_csv} to Timeline.js JSON...")
        print(f"Scale: {args.scale}")
        print(f"Validation: {'enabled' if args.validate else 'disabled'}")
        
        timeline_data = converter.convert_csv_to_json(args.input_csv)
        
        # Write output file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(timeline_data, f, indent=2, ensure_ascii=False)
        
        # Show statistics
        stats = {
            'title': 1 if 'title' in timeline_data else 0,
            'events': len(timeline_data.get('events', [])),
            'eras': len(timeline_data.get('eras', []))
        }
        
        print(f"\n✅ Conversion successful!")
        print(f"📁 Output: {output_file}")
        print(f"📊 Statistics:")
        print(f"   • Title slide: {stats['title']}")
        print(f"   • Events: {stats['events']}")
        print(f"   • Eras: {stats['eras']}")
        
        if converter.warnings:
            print(f"\n⚠️  Warnings ({len(converter.warnings)}):")
            for warning in converter.warnings[:5]:  # Show first 5 warnings
                print(f"   • {warning}")
            if len(converter.warnings) > 5:
                print(f"   • ... and {len(converter.warnings) - 5} more warnings")
        
        # Media type detection summary
        if args.stats:
            media_types = {}
            for item in timeline_data.get('events', []) + [timeline_data.get('title', {})]:
                if 'media' in item and 'url' in item['media']:
                    media_type = MediaTypeDetector.detect_type(item['media']['url'])
                    media_types[media_type['name']] = media_types.get(media_type['name'], 0) + 1
            
            if media_types:
                print(f"\n📺 Media Types Detected:")
                for media_type, count in sorted(media_types.items()):
                    print(f"   • {media_type}: {count}")
        
        print(f"\n🚀 Ready to use with Timeline.js!")
        
    except TimelineError as e:
        print(f"\n❌ Error: {str(e)}")
        return 1
    except KeyboardInterrupt:
        print(f"\n⏹️  Conversion cancelled by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        if args.validate:
            print("Try running without --validate for more lenient processing")
        return 1

def validate_timeline_json(json_file_path: str) -> bool:
    """Validate a Timeline.js JSON file"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Basic structure validation
        if not isinstance(data, dict):
            print("❌ JSON must be an object")
            return False
        
        # Check for events or title
        has_title = 'title' in data and data['title']
        has_events = 'events' in data and len(data.get('events', [])) > 0
        
        if not has_title and not has_events:
            print("❌ Timeline must have either a title or events")
            return False
        
        # Validate events
        if 'events' in data:
            for i, event in enumerate(data['events']):
                if not isinstance(event, dict):
                    print(f"❌ Event {i+1} must be an object")
                    return False
                
                if 'start_date' not in event:
                    print(f"❌ Event {i+1} missing required 'start_date'")
                    return False
                
                # Validate date structure
                start_date = event['start_date']
                if not isinstance(start_date, dict) or 'year' not in start_date:
                    print(f"❌ Event {i+1} has invalid start_date structure")
                    return False
        
        # Validate eras
        if 'eras' in data:
            for i, era in enumerate(data['eras']):
                if not isinstance(era, dict):
                    print(f"❌ Era {i+1} must be an object")
                    return False
                
                if 'start_date' not in era or 'end_date' not in era:
                    print(f"❌ Era {i+1} missing required start_date or end_date")
                    return False
        
        print("✅ Timeline JSON is valid!")
        return True
        
    except FileNotFoundError:
        print(f"❌ File not found: {json_file_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        return False

class InteractiveConverter:
    """Interactive mode for CSV to JSON conversion"""
    
    def __init__(self):
        self.converter = TimelineConverter()
    
    def run(self):
        """Run interactive conversion mode"""
        print("🕒 Timeline.js Interactive CSV Converter")
        print("=" * 50)
        
        # Get input file
        while True:
            csv_file = input("\n📁 Enter CSV file path (or 'quit' to exit): ").strip()
            if csv_file.lower() == 'quit':
                return
            
            if os.path.exists(csv_file):
                break
            print(f"❌ File not found: {csv_file}")
        
        # Get options
        print("\n⚙️  Configuration Options:")
        
        scale = self._get_choice("Timeline scale", ['human', 'cosmological'], 'human')
        validate = self._get_yes_no("Enable validation", True)
        
        # Get output file
        base_name = os.path.splitext(csv_file)[0]
        default_output = f"{base_name}_timeline.json"
        output_file = input(f"\n💾 Output file [{default_output}]: ").strip()
        if not output_file:
            output_file = default_output
        
        # Convert
        try:
            print(f"\n🔄 Converting {csv_file}...")
            self.converter = TimelineConverter(scale=scale, validate=validate)
            timeline_data = self.converter.convert_csv_to_json(csv_file)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(timeline_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Success! Created {output_file}")
            
            # Show preview
            if self._get_yes_no("Show JSON preview", False):
                print("\n" + "─" * 50)
                print(json.dumps(timeline_data, indent=2)[:1000] + "...")
                print("─" * 50)
            
            # Validate output
            if self._get_yes_no("Validate output", True):
                validate_timeline_json(output_file)
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def _get_choice(self, prompt: str, choices: List[str], default: str) -> str:
        """Get user choice from options"""
        choices_str = "/".join(f"[{c}]" if c == default else c for c in choices)
        while True:
            choice = input(f"{prompt} ({choices_str}): ").strip().lower()
            if not choice:
                return default
            if choice in choices:
                return choice
            print(f"Invalid choice. Options: {', '.join(choices)}")
    
    def _get_yes_no(self, prompt: str, default: bool) -> bool:
        """Get yes/no input from user"""
        default_str = "[Y/n]" if default else "[y/N]"
        while True:
            choice = input(f"{prompt} {default_str}: ").strip().lower()
            if not choice:
                return default
            if choice in ['y', 'yes']:
                return True
            if choice in ['n', 'no']:
                return False
            print("Please enter 'y' or 'n'")

def analyze_csv(csv_file_path: str):
    """Analyze CSV file and provide insights"""
    print(f"🔍 Analyzing {csv_file_path}...")
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8', newline='') as csvfile:
            # Detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            delimiter = ','
            if sample.count('\t') > sample.count(','):
                delimiter = '\t'
            elif sample.count(';') > sample.count(','):
                delimiter = ';'
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            rows = list(reader)
        
        if not rows:
            print("❌ CSV file is empty")
            return
        
        print(f"📊 CSV Analysis Results:")
        print(f"   • Total rows: {len(rows)}")
        print(f"   • Columns: {len(reader.fieldnames)}")
        print(f"   • Delimiter: '{delimiter}'")
        
        # Analyze types
        type_counts = {}
        for row in rows:
            row_type = row.get('Type', '').lower()
            type_counts[row_type] = type_counts.get(row_type, 0) + 1
        
        print(f"   • Row types:")
        for type_name, count in sorted(type_counts.items()):
            print(f"     - {type_name or 'empty'}: {count}")
        
        # Analyze date coverage
        dates = []
        for row in rows:
            start_date = row.get('Start Date', '')
            if start_date:
                try:
                    date_obj = DateParser.parse_date(start_date)
                    if date_obj and 'year' in date_obj:
                        dates.append(date_obj['year'])
                except:
                    pass
        
        if dates:
            print(f"   • Date range: {min(dates)} - {max(dates)}")
            print(f"   • Time span: {max(dates) - min(dates)} years")
        
        # Analyze media usage
        media_count = sum(1 for row in rows if row.get('Media URL', ''))
        print(f"   • Rows with media: {media_count}/{len(rows)} ({media_count/len(rows)*100:.1f}%)")
        
        # Check for common issues
        issues = []
        for i, row in enumerate(rows, 1):
            if not row.get('Headline', ''):
                issues.append(f"Row {i}: Missing headline")
            
            row_type = row.get('Type', '').lower()
            if row_type in ['event', 'era'] and not row.get('Start Date', ''):
                issues.append(f"Row {i}: Missing start date")
            
            if row_type == 'era' and not row.get('End Date', ''):
                issues.append(f"Row {i}: Era missing end date")
        
        if issues:
            print(f"\n⚠️  Potential Issues ({len(issues)}):")
            for issue in issues[:5]:
                print(f"   • {issue}")
            if len(issues) > 5:
                print(f"   • ... and {len(issues) - 5} more issues")
        else:
            print(f"\n✅ No obvious issues detected!")
        
    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")

if __name__ == "__main__":
    # Add additional command-line options
    if len(sys.argv) > 1:
        # Check for special commands
        if sys.argv[1] == '--interactive':
            InteractiveConverter().run()
            sys.exit(0)
        elif sys.argv[1] == '--analyze' and len(sys.argv) > 2:
            analyze_csv(sys.argv[2])
            sys.exit(0)
        elif sys.argv[1] == '--validate-json' and len(sys.argv) > 2:
            validate_timeline_json(sys.argv[2])
            sys.exit(0)
    
    # Regular command-line processing
    sys.exit(main() or 0)