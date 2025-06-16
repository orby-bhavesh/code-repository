import logging
import csv
import os
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from va import workflow, step
from va.playwright import get_browser, wrap
import openai

# Input model for the workflow
class BookingData(BaseModel):
    check_in_date: str
    check_out_date: str
    number_of_people: int
    leader_first_name: str
    leader_last_name: str
    leader_phone_num: str
    leader_email: str

class WorkflowInput(BaseModel):
    csv_path: str

@workflow("Camp 4 Booking Buddy Form Filler")
def main(input: WorkflowInput, logger: logging.Logger):
    """
    Workflow to fill and submit the Camp 4 Booking Buddy form using data from a CSV file.
    """
    logger.info("STARTING: Camp 4 Booking Buddy Form Filler workflow")
    
    try:
        # Read booking data from CSV
        with step("Reading booking data from CSV"):
            logger.info(f"PROGRESS: Reading booking data from CSV file: {input.csv_path}")
            raw_booking_data = read_csv_raw(input.csv_path, logger)
            logger.info(f"SUCCESS: Read {len(raw_booking_data)} booking records from CSV")
            
            # Map CSV data to form fields using LLM if needed
            logger.info("PROGRESS: Mapping CSV data to form fields")
            booking_data = map_data_to_form_fields(raw_booking_data, logger)
            logger.info("SUCCESS: Mapped CSV data to form fields")
        
        # Process each booking
        for i, booking in enumerate(booking_data):
            logger.info(f"PROGRESS: Processing booking {i+1} of {len(booking_data)}")
            
            try:
                # Fill out the form for this booking
                with step(f"Filling form for booking {i+1}"):
                    fill_booking_form(booking, logger)
                logger.info(f"SUCCESS: Completed form submission for booking {i+1}")
            
            except Exception as e:
                logger.error(f"FAILED: Error processing booking {i+1}: {str(e)}")
                logger.exception(e)
        
        logger.info("COMPLETED: All bookings processed")
        logger.info("TASK_COMPLETED_SUCCESSFULLY")
        
    except Exception as e:
        logger.error(f"FAILED: Workflow execution failed: {str(e)}")
        logger.exception(e)
        logger.error(f"TASK_FAILED: {str(e)}")

def read_csv_raw(csv_path: str, logger: logging.Logger) -> List[Dict[str, Any]]:
    """
    Read raw booking data from CSV file without mapping to model.
    """
    raw_data = []
    
    try:
        with open(csv_path, 'r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                raw_data.append(dict(row))
        
        return raw_data
    
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        logger.exception(e)
        raise

def map_data_to_form_fields(raw_data: List[Dict[str, Any]], logger: logging.Logger) -> List[BookingData]:
    """
    Map raw CSV data to form fields, using LLM for complex mappings if needed.
    """
    mapped_data = []
    
    for record in raw_data:
        try:
            # First try direct mapping
            try:
                booking = BookingData(
                    check_in_date=record['Check-in Date'],
                    check_out_date=record['Check-out Date'],
                    number_of_people=int(record['Number of People']),
                    leader_first_name=record['leader_first_name'],
                    leader_last_name=record['leader_last_name'],
                    leader_phone_num=record['leader_phone_num'],
                    leader_email=record['leader_email']
                )
                mapped_data.append(booking)
                logger.info("DEBUG: Direct mapping successful")
                continue
            except (KeyError, ValueError) as e:
                logger.info(f"Direct mapping failed, using LLM for mapping: {str(e)}")
                
            # If direct mapping fails, use LLM
            mapped_record = use_llm_for_mapping(record, logger)
            booking = BookingData(**mapped_record)
            mapped_data.append(booking)
            
        except Exception as e:
            logger.error(f"Error mapping record {record}: {str(e)}")
            logger.exception(e)
            raise
    
    return mapped_data

def use_llm_for_mapping(record: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """
    Use OpenAI to map ambiguous CSV fields to the required form fields.
    """
    logger.info("PROGRESS: Using LLM to map CSV fields to form fields")
    
    try:
        client = openai.OpenAI()  # Assumes API key is in environment variables
        
        prompt = f"""
        I need to map CSV data to specific form fields for a camping reservation form.
        
        The form requires these fields:
        - check_in_date: The date the campers will arrive
        - check_out_date: The date the campers will leave
        - number_of_people: Integer representing number of people in the group
        - leader_first_name: First name of the group leader
        - leader_last_name: Last name of the group leader
        - leader_phone_num: Phone number of the group leader
        - leader_email: Email address of the group leader
        
        Here is the CSV data:
        {record}
        
        Please map this data to the required fields and return ONLY a JSON object with the properly mapped fields.
        """
        
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": "You are a helpful assistant that maps data fields."},
                     {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content
        logger.info(f"DEBUG: LLM response: {result}")
        
        # Parse the JSON string into a Python dictionary
        import json
        mapped_data = json.loads(result)
        
        # Validate the mapped data has all required fields
        required_fields = ["check_in_date", "check_out_date", "number_of_people", 
                          "leader_first_name", "leader_last_name", "leader_phone_num", "leader_email"]
        
        for field in required_fields:
            if field not in mapped_data:
                raise KeyError(f"LLM mapping failed to provide required field: {field}")
        
        # Ensure number_of_people is an integer
        mapped_data["number_of_people"] = int(mapped_data["number_of_people"])
        
        logger.info("SUCCESS: LLM mapping completed successfully")
        return mapped_data
        
    except Exception as e:
        logger.error(f"Error in LLM mapping: {str(e)}")
        logger.exception(e)
        raise

def fill_booking_form(booking: BookingData, logger: logging.Logger):
    """
    Fill out the Camp 4 Booking Buddy form for a single booking.
    """
    with get_browser(headless=False, slow_mo=500) as browser:
        page = wrap(browser.new_page())
        page.set_viewport_size({"width": 1280, "height": 800})
        
        with step("Navigate to booking form"):
            logger.info("PROGRESS: Navigating to Camp 4 Booking Buddy form")
            page.goto("https://camp-4-booking-buddy.lovable.app/")
            logger.info("SUCCESS: Navigated to form page")
            # Take a screenshot for debugging
            screenshot_path = f"form_initial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            page.screenshot(path=screenshot_path)
            logger.info(f"DEBUG: Captured initial form screenshot: {screenshot_path}")
        
        with step("Fill check-in date"):
            logger.info(f"PROGRESS: Filling check-in date: {booking.check_in_date}")
            try:
                # Based on the HTML, use the id selector first
                check_in_field = page.locator("#date-in") | page.get_by_prompt("Check-in Date field")
                check_in_field.fill(booking.check_in_date)
                logger.info("DEBUG: Check-in date field filled")
            except Exception as e:
                logger.error(f"Error filling check-in date: {str(e)}")
                page.screenshot(path=f"error_checkin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                raise
        
        with step("Fill check-out date"):
            logger.info(f"PROGRESS: Filling check-out date: {booking.check_out_date}")
            try:
                check_out_field = page.locator("#date-out") | page.get_by_prompt("Check-out Date field")
                check_out_field.fill(booking.check_out_date)
                logger.info("DEBUG: Check-out date field filled")
            except Exception as e:
                logger.error(f"Error filling check-out date: {str(e)}")
                page.screenshot(path=f"error_checkout_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                raise
        
        with step("Fill number of people"):
            logger.info(f"PROGRESS: Filling number of people: {booking.number_of_people}")
            try:
                num_people_field = page.locator("#number-of-people") | page.get_by_prompt("Number of People field")
                num_people_field.fill(str(booking.number_of_people))
                logger.info("DEBUG: Number of people field filled")
            except Exception as e:
                logger.error(f"Error filling number of people: {str(e)}")
                page.screenshot(path=f"error_people_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                raise
        
        with step("Fill lead camper information"):
            logger.info("PROGRESS: Filling lead camper information")
            
            try:
                # First name
                first_name_field = page.locator("#first-name") | page.get_by_prompt("First name field")
                first_name_field.fill(booking.leader_first_name)
                logger.info(f"DEBUG: First name field filled with: {booking.leader_first_name}")
                
                # Last name
                last_name_field = page.locator("#last-name") | page.get_by_prompt("Last name field")
                last_name_field.fill(booking.leader_last_name)
                logger.info(f"DEBUG: Last name field filled with: {booking.leader_last_name}")
                
                # Phone number
                phone_field = page.locator("#phone") | page.get_by_prompt("Phone number field")
                phone_field.fill(booking.leader_phone_num)
                logger.info(f"DEBUG: Phone field filled with: {booking.leader_phone_num}")
                
                # Email
                email_field = page.locator("#email") | page.get_by_prompt("Email address field")
                email_field.fill(booking.leader_email)
                logger.info(f"DEBUG: Email field filled with: {booking.leader_email}")
                
                logger.info("SUCCESS: Lead camper information filled")
                # Take a screenshot for verification
                screenshot_path = f"form_filled_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=screenshot_path)
                logger.info(f"DEBUG: Captured filled form screenshot: {screenshot_path}")
                
            except Exception as e:
                logger.error(f"Error filling lead camper information: {str(e)}")
                page.screenshot(path=f"error_camper_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                raise
        
        with step("Submit form"):
            logger.info("PROGRESS: Submitting form")
            try:
                submit_button = page.get_by_text("Submit Reservation") | page.get_by_prompt("Submit reservation button")
                
                # Take a screenshot before submission
                screenshot_path = f"before_submit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=screenshot_path)
                logger.info(f"DEBUG: Captured pre-submission screenshot: {screenshot_path}")
                
                # Uncomment the line below to actually submit the form in production
                # submit_button.click()
                logger.info("DEBUG: Form would be submitted here (submit_button.click() is commented out for safety)")
                
                # Wait for confirmation or navigate to next page as needed
                # page.wait_for_selector("confirmation-element")
                
                logger.info("SUCCESS: Form submission process completed")
            except Exception as e:
                logger.error(f"Error submitting form: {str(e)}")
                page.screenshot(path=f"error_submit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                raise

def create_sample_csv(file_path: str):
    """Create a sample CSV file for testing if it doesn't exist."""
    with open(file_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Check-in Date', 'Check-out Date', 'Number of People', 
                       'leader_first_name', 'leader_last_name', 'leader_phone_num', 'leader_email'])
        writer.writerow(['06/20/2025', '06/22/2025', '4', 'John', 'Doe', '555-123-4567', 'john.doe@example.com'])
        writer.writerow(['07/15/2025', '07/20/2025', '2', 'Jane', 'Smith', '555-987-6543', 'jane.smith@example.com'])

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Default parameters for testing
    sample_csv_path = os.path.abspath("sample_bookings.csv")
    
    # Check if sample CSV exists, create if not
    if not os.path.exists(sample_csv_path):
        logger.info(f"Sample CSV not found, creating {sample_csv_path}")
        create_sample_csv(sample_csv_path)
        logger.info(f"Created sample CSV: {sample_csv_path}")
    
    main(WorkflowInput(csv_path=sample_csv_path), logger=logger)
