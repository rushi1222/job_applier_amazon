import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait,Select
from selenium.webdriver.support import expected_conditions as EC
from itertools import product
import traceback
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

applied_jobs_file = 'applied_jobs.txt'
failed_jobs_file = 'failed_jobs.txt'
failed_jobs = []


class AmazonJobApplier:
    def __init__(self, parameters, driver):
        self.browser = driver
        self.email = parameters.get('email')
        self.password = parameters.get('password')
        self.amazon_url = parameters.get('amazon_url')
        
        self.positions = parameters.get('positions', [])
        self.locations = parameters.get('locations', [])
        self.seen_jobs = []  # Keep track of jobs you've already applied for
        self.title_blacklist = parameters.get('titleBlacklist', []) or []
        self.company_blacklist = []  # Add companies to this list if needed
        self.company_blacklist = parameters.get('companyBlacklist', []) or []
        self.contact_info = parameters.get('contact', {})
        self.experience = parameters.get('experience', {})
        self.submission = False  # Flag to track successful submission


    def login(self):
        print("Starting the login process...")
        self.browser.get(self.amazon_url)
        print(f"Navigated to {self.amazon_url}")

        #can u make the browser window full screen
        self.browser.maximize_window()
        
        time.sleep(3)  # Wait for the page to load

        # Step 1: Accept cookies if necessary
        try:
            print("Trying to find the 'Accept All' button for cookies...")
            accept_cookies_button = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//b[contains(text(), 'Accept all')]]"))
            )
            accept_cookies_button.click()
            print("Cookies accepted successfully.")
        except Exception as e:
            print(f"Failed to click the 'Accept All' button: {e}")
        
        time.sleep(3)

        # Step 2: Enter email and password and log in
        try:
            print(f"Attempting to enter email: {self.email}")
            email_input = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            email_input.send_keys(self.email)
            print("Email entered successfully.")
            
            continue_button = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.ID, "sign-in-button"))
            )
            continue_button.click()
            print("Continue button clicked successfully.")
            
            time.sleep(3)
            
            print(f"Attempting to enter password.")
            password_input = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_input.send_keys(self.password)
            print("Password entered successfully.")
            
            login_button = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Log in')]"))
            )
            login_button.click()
            print("Log in button clicked successfully.")

            # Skip MFA if necessary
            time.sleep(3)
            skip_mfa_button = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.ID, "bypassOptionalMfaButton"))
            )
            skip_mfa_button.click()
            print("MFA skipped successfully.")

        except Exception as e:
            print(f"Error during login process: {e}")

    def search_jobs(self):
        print("Navigating to the job search page...")
        time.sleep(3)

        # Generate all combinations of positions and locations
        searches = list(product(self.positions, self.locations))
        print(f"Generated searches: {searches}")

        # Shuffle searches if needed
        random.shuffle(searches)

        page_sleep = 0
        minimum_time = 60 * 15  # minimum time bot should run before taking a break
        minimum_page_time = time.time() + minimum_time

        # Iterate over each combination of position and location
        for position, location in searches:
            position_query = position.replace(' ', '+')
            location_query = location.replace(' ', '+')

            print(f"Position Query: {position_query}")
            print(f"Location Query: {location_query}")

            search_url = f"https://www.amazon.jobs/en/search?base_query={position_query}&loc_query={location_query}"
            print(f"Navigating to search URL: {search_url}")
            self.browser.get(search_url)
            time.sleep(3)

            search_button = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Search jobs']"))
            )
            search_button.click()
            time.sleep(1)
            search_button.click()
            time.sleep(2)

            job_page_number = 0

            try:
                while True:
                    job_page_number += 1
                    print(f"Going to job page {job_page_number} for position: {position} in {location}")

                    self.apply_jobs(location)

                    print(f"Job applications on page {job_page_number} completed successfully.")

                    # time_left = minimum_page_time - time.time()
                    # if time_left > 0:
                    #     print(f"Sleeping for {time_left} seconds.")
                    #     time.sleep(time_left)
                    #     minimum_page_time = time.time() + minimum_time

                    # if page_sleep % 5 == 0:
                    #     sleep_time = random.randint(180, 300)  # Take a break between 3 to 5 minutes
                    #     print(f"Taking a break for {sleep_time / 60} minutes.")
                    #     time.sleep(sleep_time)
                    #     page_sleep += 1

                    # Check if pagination exists before moving to the next page
                    try:
                        next_page_button = self.browser.find_element(By.XPATH, "//a[@aria-label='Next page']")
                        next_page_button.click()
                        time.sleep(3)
                    except:
                        # If the pagination button is not found, assume no more pages and break
                        print("No more pages or pagination button not found. Exiting loop.")
                        break

                    # Logic to break the loop, for example, after all jobs are applied on the page
                    if self.no_more_jobs():  # Placeholder function
                        print("No more jobs found, breaking the loop.")
                        break

            except Exception as e:
                print(f"An error occurred during the job application process: {e}")
                traceback.print_exc()


    def apply_jobs(self, location):
        try:
            job_tiles = WebDriverWait(self.browser, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'job-tile'))
            )
            
            skipped_jobs = 0  # Counter for skipped jobs
            num_jobs = len(job_tiles)
            print(f"Number of jobs found: {num_jobs}")

            for i in range(num_jobs):
                # Re-fetch the job tiles after navigating back to ensure no stale element reference
                job_tiles = WebDriverWait(self.browser, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, 'job-tile'))
                )
                job_tile = job_tiles[i]

                job_title = job_tile.find_element(By.CLASS_NAME, 'job-title').text
                job_link = job_tile.find_element(By.CLASS_NAME, 'job-link').get_attribute('href')
                job_id = job_tile.find_element(By.CLASS_NAME, 'location-and-id').text.split('Job ID: ')[-1]

                print("Job ID: ", job_id)
                print("Job Title: ", job_title)
                print("Job Link: ", job_link)
                
                if job_id in self.seen_jobs or job_id in failed_jobs:
                    print(f"Already applied to {job_title}. Skipping.")
                    skipped_jobs += 1
                    continue

                if any(bl_word in job_title.lower() for bl_word in self.title_blacklist):
                    print(f"Job title '{job_title}' is blacklisted. Skipping.")
                    skipped_jobs += 1
                    continue

                self.browser.get(job_link)
                time.sleep(3)

                if self.apply_to_job(job_title, location, job_link, job_id, self.submission) is True or \
                self.apply_to_job(job_title, location, job_link, job_id, self.submission) == "Already Applied":
                    self.browser.back()
                    print("back1")
                    time.sleep(3)  # Increased wait time to ensure the page reloads properly
                    self.seen_jobs.append(job_id)   
                    # self.log_job_success(job_id)

                # Navigate back to the previous page (job listings)
                self.browser.back()
                print("back2")
                time.sleep(3)  # Increased wait time to ensure the page reloads properly

            if skipped_jobs == len(job_tiles):
                print("All jobs on this page have been applied. Exiting...")
                return  # Exit if all jobs are skipped

        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()


    def log_job_success(self, job_id, job_title, job_link):
        """Log successful job application."""
        application_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        try:
            with open(applied_jobs_file, 'a') as f:
                f.write(f"{job_id},{job_title},{job_link},{application_time}\n")
            print(f"Logged job {job_id} as successfully applied.")
        except Exception as e:
            print(f"Failed to log successful application for job {job_id}: {e}")


    def log_job_failure(self, job_id, job_title, job_link):
        """Log failed job application, only if job_id is valid."""
        application_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        try:
            with open(failed_jobs_file, 'a') as f:
                f.write(f"{job_id},{job_title},{job_link},{application_time}\n")
                print(f"Logged job {job_id} as successfully applied.")
        except Exception as e:
            print(f"Failed to log successful application for job {job_id}: {e}")

    def apply_to_job(self, job_title, job_location, job_link, job_id, submission):
        # Add your logic to apply for the job
        print(f"Applying to job: {job_title} in {job_location}")
        print(f"Job ID: {job_id}")
        print(f"Job Link: {job_link}")
        print("Application status: ", submission)

        
        # <div class="apply"><a id="apply-button" class="btn btn-primary " aria-label="Apply now for iOS Engineer" href="https://www.amazon.jobs/applicant/jobs/2788377/apply">Apply now</a></div>
        try:
            apply_button = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.ID, "apply-button"))
            )
            apply_button.click()
            print("Apply button clicked successfully.")
            time.sleep(3)
            submission = self.application_form()  # Return True or False
            print("Submission status: ", submission)
            if submission == True:
                print("Application successfully submitted.")
                self.log_job_success(job_id,job_title, job_link)
            elif submission == "Already Applied":
                print("Already applied for this position inside apply_to_job.")
                submission = True
            else:
                print("Application failed during submission.")
                self.log_job_failure(job_id,job_title, job_link)
            return submission
            
        except:
            print("Apply button not found. Skipping job.")
            return False

        return True
    
    def no_more_jobs(self):
        # Placeholder function to determine if there are more jobs to apply for
        return False
    
    def application_form(self):
        # Assuming the browser (driver) is already initialized and points to the correct page
        try:

            try:

                # Wait with WebDriverWait to locate the element then check
                alreadyApplied = WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "application-already-exist"))
                )
                if alreadyApplied:
                    print("Already applied for this position")
                    return "Already Applied"
            except:
                # Locate the Contact Information link by its ID using the browser
                contact_info = self.browser.find_element(By.ID, "NAV_CONTACT_DETAILS")

                # Remove this part after testing and uncomment the parts
                #############################################################################################
                sms_verification = self.browser.find_element(By.ID, "NAV_SMS_NOTIFICATIONS")
                time.sleep(4)  # Wait for the selection to process
                print("Located SMS Verification link.")
                sms_verification.click()
                print("Successfully selected 'SMS Verification'")
                time.sleep(4)  # Wait for the selection to process     

                self.click_skip_continue_button(delay=1)
                time.sleep(4)  # Wait for the selection to process
                #############################################################################################

                # Uncomment this part for production use
                # # Click on the "Contact information" link
                # contact_info.click()
                # print("Successfully selected 'Contact Information'")
                # time.sleep(10)
                # self.contact_information_form()
                # self.sms_verification_form()

                #############################################################################################
                # # Locate the Job Specific link by its ID using the browser
                # if self.browser.find_element(By.XPATH, "//a[contains(text(), 'Job-specific questions')]"):
                #     print("Job-specific questions found.")
                #     self.job_specific_questions_form()
                # else:
                #     print("No job-specific questions found.")
                #############################################################################################

                #############################################################################################
                # # Locate the Work Eligibility link by its ID using the browser
                if self.browser.find_element(By.XPATH, "//a[contains(text(), 'Work Eligibility')]"):
                    print("Work Eligibility found.")
                    self.work_eligibility_form()

                # Example of locating the "Review & submit" link:
                # <li id="NAV_SUBMIT" class="form-list-item arrow_box review-submit single-top-form-or-last-section-form
                # last-item active next-form" data-direct-call-identifier="nav_app_review_submit" role="presentation">
                # <a href="javascript:void(0)" role="tab" class="form-link nav-link single-top-form-or-last-sub-form"
                # aria-label="review all application forms" aria-selected="true" aria-controls="REVIEW_AND_SUBMIT"
                # tabindex="0">Review &amp; submit</a></li>
                if self.browser.find_element(By.XPATH, "//a[contains(text(), 'Review & submit')]"):
                    print("Review & submit found.")
                    submission = self.review_submit_form()
                    return submission
                else:
                    print("No Review & submit found.")
                    return False
        except Exception as e:
            print(f"Error occurred: {e}")



    def work_eligibility_form(self):
        try:
            # Locate the Work Eligibility link by its ID
            work_eligibility = self.browser.find_element(By.ID, "NAV_WORK_ELIGIBILITY_EXTERNAL_USA")
            time.sleep(4)  # Wait for the selection to process
            print("Located Work Eligibility link.")
            work_eligibility.click()
            print("Successfully selected 'Work Eligibility'")
            time.sleep(4)  # Wait for the selection to process

            # Locate the Work Eligibility questions section
            work_specific_questions = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Work Eligibility']"))
            )
            time.sleep(2)  # Short pause after clicking
            form = WebDriverWait(work_specific_questions, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            print("Located form inside Work Eligibility div.")

            # Locate all form groups
            form_groups = form.find_elements(By.CLASS_NAME, "form-group")
            print(f"Number of form groups found: {len(form_groups)}")

            # Process each form group
            for form_group in form_groups:
                # Identify the question
                question_text = self.identify_question(form_group)
                print(f"Question identified: {question_text}")

                # Check for sponsorship-related question
                if "sponsorship" in question_text.lower():
                    print("Sponsorship-related question found.")
                    self.work_eligibility_answer(form_group, "NO")

                # Check for government employment-related question
                elif "government" in question_text.lower():
                    print("Government employment-related question found.")
                    self.work_eligibility_answer(form_group, "NEVER")

            # Locate the "Save & continue" button by its ID and click it
            self.button_continue()  # Click the "Continue" button after filling the form

        except Exception as e:
            print(f"Error occurred while filling the Work Eligibility form: {e}")
            traceback.print_exc()


    def work_eligibility_answer(self, form_group, answer_value):
        """Handle specific questions by selecting the appropriate radio button."""
        try:
            # Locate the radio group inside the form group
            radio_group = form_group.find_element(By.CLASS_NAME, "radio-field")
            print("Located radio group.")

            # Locate the radio button with the specified value and click it
            radio_button = radio_group.find_element(By.XPATH, f".//input[@value='{answer_value}']")
            label_for_radio = radio_group.find_element(By.XPATH, f".//label[@for='{radio_button.get_attribute('id')}']")

            # Check if the radio button is already selected
            is_selected = radio_button.get_attribute("aria-checked") == "true"
            if not is_selected:
                # Click the label instead of the input to avoid interception
                label_for_radio.click()
                print(f"Selected radio button with value: {answer_value} by clicking the label.")
                time.sleep(2)  # Pause to ensure the selection is processed
            else:
                print(f"Radio button with value '{answer_value}' is already selected.")

        except Exception as e:
            print(f"Error occurred while handling specific question: {e}")
            traceback.print_exc()





    def job_specific_questions_form(self):
        try:

            job_specific_li = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.XPATH, "//li[a[contains(@aria-label, 'Job-specific questions form')]]"))
            )
            print("Located the <li> element.")

            # Extract the ID of the located <li>
            li_id = job_specific_li.get_attribute("id")
            print(f"ID of the <li>: {li_id}")

            # Click on the element using the ID
            element_to_click = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.ID, li_id))
            )
            element_to_click.click()
            print(f"Clicked on the <li> with ID: {li_id}")
            # Locate the job-specific questions section
            job_specific_questions = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Job-specific questions']"))
            )


            time.sleep(2)  # Short pause after clicking
            form = WebDriverWait(job_specific_questions, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            print("Located form inside Job-specific questions div.")
            
            # Locate all form groups
            form_groups = form.find_elements(By.CLASS_NAME, "form-group")
            print(f"Number of form groups found: {len(form_groups)}")
            
            # Process each form group
            for form_group in form_groups:
                # Identify the question
                question_text = self.identify_question(form_group)
                print(f"Question identified: {question_text}")
                
                # Answer the question
                self.answer_question(form_group)

            # Click the "Continue" button after filling the form
            print("all questions answered")
            self.button_continue()


        except Exception as e:
            print(f"Error occurred while filling the job-specific questions form: {e}")
            traceback.print_exc()

    def identify_question(self, form_group):
        """Identify and return the question text from the form group."""
        try:
            # Use XPath to exclude sr-only elements and capture only visible label text
            question_text = form_group.find_element(By.XPATH, ".//label[not(span[@class='sr-only'])]").text
            return question_text
        except Exception as e:
            print(f"Error identifying question in form group: {e}")
            traceback.print_exc()
            return None

    def answer_question(self, form_group):
        """Click the dropdown and select the appropriate option."""
        try:
            # Step 1: Locate the dropdown trigger dynamically
            dropdown_trigger = form_group.find_element(By.CLASS_NAME, "select2-selection--single")
            print("Located dropdown trigger.")
            # Short pause to ensure it's rendered
            time.sleep(2)

            # Scroll into view and ensure it's clickable
            self.browser.execute_script("arguments[0].scrollIntoView(true);", dropdown_trigger)
            print("Scrolled to dropdown trigger.")
            time.sleep(2)  # Short pause after scrolling

            WebDriverWait(self.browser, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "select2-selection--single"))
            )
            print("Dropdown trigger is clickable.")

            dropdown_trigger.click()
            print("Dropdown clicked successfully.")
            time.sleep(2)  # Short pause to allow dropdown animation

            # Step 2: Wait for the dropdown to expand
            WebDriverWait(self.browser, 5).until(
                EC.element_attribute_to_include((By.CLASS_NAME, "select2-selection--single"), "aria-expanded")
            )
            print("Dropdown expanded.")
            time.sleep(2)  # Short pause for expansion

            # Step 3: Locate the list of dropdown options dynamically
            dropdown_options = WebDriverWait(self.browser, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//ul[@class='select2-results__options']/li"))
            )
            print(f"Number of dropdown options: {len(dropdown_options)}")
            time.sleep(3)  # Brief pause to ensure options are fully loaded

                    # Print the options for debugging
            for option in dropdown_options:
                print(f"Option text: {option.text.strip()}")

            # Step 4: Check for "Yes" option, otherwise select the last option
            selected_option_text = None
            for option in dropdown_options:
                if option.text.strip().lower() == "yes":
                    print("Found 'Yes' option.")
                    option_text = option.text
                    print(f"Found 'Yes' option: {option_text}")
                    option.click() # Click the "Yes" option
                    print("Clicked 'Yes' option.")
                    selected_option_text = option_text
                    print(f"Selected 'Yes' option: {selected_option_text}")
                    break
            else:
                # If no "Yes" option, select the last option
                if dropdown_options:
                    last_option = dropdown_options[-1]
                    last_option_text = last_option.text  # Capture text before clicking
                    last_option.click()
                    selected_option_text = last_option_text
                    print(f"Selected last option: {selected_option_text}")
                else:
                    print("No options found in the dropdown.")
            time.sleep(2)  # Short pause to allow selection to complete

        except Exception as e:
            print(f"Error interacting with the dropdown: {e}")
            traceback.print_exc()
            time.sleep(5)  # Longer pause for error analysis


    def review_submit_form(self):
        # <div class="submit-application-stickey-container py-3 position-sticky"><div class="container d-flex justify-content-end"><div class="submit-application-button"><button class="btn btn-primary submit" type="submit" role="button">Submit application</button></div></div></div>
        try:
            # Locate the "Submit application" button by its class name
            submit_button = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and contains(@class, 'submit')]"))
            )
            print("Located 'Submit application' button.")

            # Scroll into view to ensure it's within the viewport
            self.browser.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            print("Scrolled to 'Submit application' button.")
            time.sleep(2)  # Optional pause after scrolling

            # Ensure the button is clickable
            WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and contains(@class, 'submit')]")))
            print("'Submit application' button is clickable.")

            # Click the button
            submit_button.click()
            print("'Submit application' button clicked successfully.")
            time.sleep(3)
            return True
        except Exception as e:
            print(f"Error occurred while clicking the 'Submit application' button: {e}")
            traceback.print_exc()
            return False
        

    def sms_verification_form(self):
        try:
            time.sleep(2)  # Wait for the selection to process     
            # <a id="save-and-continue-form-button" href="javascript:void(0)" class="btn btn-primary mt-5">Skip &amp; continue</a>
            # Locate the "Skip & continue" button by its ID
            self.click_skip_continue_button(delay=1)

        except Exception as e:
            print(f"Error occurred while filling the SMS verification form: {e}")
            traceback.print_exc()







    def click_button(self, data_identifier=None, button_text=None, delay=1):
        """Locates, scrolls to, makes visible if hidden, and clicks a button by data attribute and/or text."""
        try:
            # Construct the XPath dynamically based on the provided data identifier and button text
            xpath = "//button"
            if data_identifier:
                xpath += f"[@data-direct-call-identifier='{data_identifier}']"
            if button_text:
                xpath += f"[contains(text(), '{button_text}')]"
            
            # Locate the button using the constructed XPath
            button = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            print(f"Located button with identifier '{data_identifier}' and text '{button_text}'.")

            # Scroll into view to ensure it's within the viewport
            self.browser.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(delay)  # Delay for scrolling
            print("Scrolled to button.")

            # Make the button visible if it's hidden by the `d-none` CSS class
            self.browser.execute_script("arguments[0].style.display = 'inline-block';", button)
            time.sleep(delay)  # Delay after forcing visibility
            print("Made button visible if hidden.")

            # Wait until the button is clickable
            WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            print("Button is clickable.")

            # Click the button
            button.click()
            print("Button clicked successfully.")
            time.sleep(3)  # Optional delay after clicking

        except Exception as e:
            print(f"Error occurred while clicking the button: {e}")

    
    def click_skip_continue_button(self, delay=1):
        """Locates, scrolls to, and clicks the 'Skip & continue' button by its ID."""
        try:
            # Locate the "Skip & continue" button by its ID
            skip_continue_button = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.ID, "save-and-continue-form-button"))
            )
            print("Located 'Skip & continue' button.")

            # Scroll into view to make sure it's within the viewport
            self.browser.execute_script("arguments[0].scrollIntoView(true);", skip_continue_button)
            time.sleep(delay)  # Brief delay to allow scrolling
            print("Scrolled to 'Skip & continue' button.")

            # Click the button
            skip_continue_button.click()
            print("'Skip & continue' button clicked successfully.")
            time.sleep(3)  # Optional delay after clicking

        except Exception as e:
            print(f"Error occurred while clicking the 'Skip & continue' button: {e}")

    def button_continue(self):
        """Locate and click the 'Continue' button."""
        try:
            # Locate the "Continue" button by its type and class
            continue_button = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[@type='button' and contains(@class, 'btn-primary')]"))
            )
            print("Located 'Continue' button.")
            
            # Scroll into view to ensure it's within the viewport
            self.browser.execute_script("arguments[0].scrollIntoView(true);", continue_button)
            print("Scrolled to 'Continue' button.")
            time.sleep(2)  # Optional pause after scrolling

            # Ensure the button is clickable
            WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and contains(@class, 'btn-primary')]")))
            print("'Continue' button is clickable.")

            # Click the button
            continue_button.click()
            print("Clicked 'Continue' button successfully.")
            time.sleep(3)  # Optional pause after clicking

        except Exception as e:
            print(f"Error occurred while clicking the 'Continue' button: {e}")
            traceback.print_exc()



    def enter_text(self, element, text, field_name="field", delay=1):
        element.clear()
        time.sleep(delay)
        element.send_keys(text)
        time.sleep(delay)
        print(f"Filled {field_name}: {text}")


    # def contact_information_form(self):
    #     try:
    #         # Locate the contact information section and click "Edit" to open the form using ID
    #         contact_section = WebDriverWait(self.browser, 10).until(
    #             EC.presence_of_element_located((By.ID, "CONTACT_DETAILS"))
    #         )
    #         print("Located CONTACT_DETAILS section.")

    #         # Locate the input fields by their IDs
    #         first_name_field = self.browser.find_element(By.ID, "applicant_first_name")
    #         print("Located first name field.")
    #         last_name_field = self.browser.find_element(By.ID, "applicant_last_name")
    #         print("Located last name field.")
    #         email_field = self.browser.find_element(By.ID, "applicant_primary_email")
    #         print("Located email field.")
    #         phone_field = self.browser.find_element(By.ID, "applicant_primary_phone_number")
    #         print("Located phone number field.")
    #         address_field_line1 = self.browser.find_element(By.ID, "applicant_address_street_line1")
    #         print("Located address line 1 field.")
    #         address_field_line2 = self.browser.find_element(By.ID, "applicant_address_street_line2")
    #         print("Located address line 2 field.")  
    #         city_field = self.browser.find_element(By.ID, "applicant_address_city")
    #         print("Located city field.")            
    #         zip_field = self.browser.find_element(By.ID, "applicant_address_zip")
    #         print("Located zip code field.")


    #         # Fill in the contact details
    #         self.enter_text(first_name_field, self.contact_info['first_name'], "first name", 2)
    #         self.enter_text(last_name_field, self.contact_info['last_name'], "last name", 2)

    #         #write a docus on the phone number and then clear the field
    #         time.sleep(2)
    #         phone_field.click()
    #         time.sleep(2)
    #         phone_field.clear()
    #         time.sleep(2)
    #         print("Cleared phone number field")
    #         phone_field.send_keys(self.contact_info['phone'])
    #         print(f"Filled phone number: {self.contact_info['phone']}")

    #         self.enter_text(address_field_line1, self.contact_info['address_line1'], "address line 1", 2)
    #         self.enter_text(address_field_line2, self.contact_info['address_line2'], "address line 2", 2)
    #         self.enter_text(city_field, self.contact_info['city'], "city", 2)
    #         self.enter_text(zip_field, self.contact_info['postal_code'], "zip code", 2)

    #         # <span class="select2 select2-container select2-container--bootstrap select2-container--above" dir="ltr" style="width: 100%;"><span class="selection"><span class="select2-selection select2-selection--single" aria-haspopup="true" aria-expanded="false" tabindex="0" aria-labelledby="addressCountry-label select2-c7q3-container addressCountry-error" role="combobox" aria-required="true" aria-invalid="false"><span class="select2-selection__rendered" id="select2-c7q3-container" role="textbox" aria-readonly="true" title="United States">United States</span><span class="select2-selection__arrow" role="presentation"><b role="presentation"></b></span></span></span><span class="dropdown-wrapper" aria-hidden="true"></span></span>                 
    #         # Select country dropdown (assuming the first instance is for country)
    #         country_dropdown = self.browser.find_elements(By.CSS_SELECTOR, "span.select2-selection--single")[0]
    #         country_dropdown.click()  # Click to open the country dropdown
    #         time.sleep(2)  # Allow the dropdown to load

    #         # Select country based on contact info
    #         country_name = self.contact_info['country']  # Example: 'United States'
    #         country_option = self.browser.find_element(By.XPATH, f"//li[text()='{country_name}']")
    #         country_option.click()
    #         print(f"Country selected: {country_name}")
    #         time.sleep(2)  # Wait for the selection to process

    #         # Select state dropdown (assuming the second instance is for state)
    #         state_dropdown = self.browser.find_elements(By.CSS_SELECTOR, "span.select2-selection--single")[1]
    #         state_dropdown.click()  # Click to open the state dropdown
    #         time.sleep(2)  # Allow the dropdown to load

    #         # Select state based on contact info
    #         state_name = self.contact_info['state']  # Example: 'New York'
    #         state_option = self.browser.find_element(By.XPATH, f"//li[text()='{state_name}']")
    #         state_option.click()
    #         print(f"State selected: {state_name}")
    #         time.sleep(2)  # Wait for the selection to process     
    #         # Scroll into view if needed
    #         self.click_button(data_identifier="contact_details", button_text="Save & continue", delay=1)
    #     except Exception as e:
    #         print(f"Error occurred while filling the contact information form: {e}")
    #         traceback.print_exc()

