import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time

class ProcasTimesheet:
    def __init__(self):
        # 1) Load environment variables from .env
        load_dotenv()

        # 2) Retrieve credentials from environment
        self.email = os.environ.get("PROCAS_EMAIL")
        self.password = os.environ.get("PROCAS_PASSWORD")

        if not self.email or not self.password:
            raise ValueError("Missing PROCAS_EMAIL or PROCAS_PASSWORD in environment variables.")

        self.driver = None
        self.base_url = "https://accounting.procas.com"

    def setup_driver(self):
        if not self.driver:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            # or other driver settings
            self.driver = webdriver.Chrome(options=options)

    def login(self):
        self.setup_driver()
        self.driver.get(self.base_url)

        # Example login flow:
        email_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "EmailAddress"))
        )
        email_field.send_keys(self.email)
        email_field.find_element(By.XPATH, "./ancestor::form").submit()

        password_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "Password"))
        )
        password_field.send_keys(self.password)
        password_field.find_element(By.XPATH, "./ancestor::form").submit()

        time.sleep(3)
        # Possibly handle a "Yes" button
        try:
            yes_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Yes')]"))
            )
            yes_button.click()
            time.sleep(2)
        except TimeoutException:
            pass

    def get_categories(self):
        """
        Retrieves a list of categories from the currently open timesheet.
        """
        self.login()
        
        # Navigate to "Edit an Open Timesheet"
        edit_link = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Edit an Open Timesheet')]"))
        )
        edit_link.click()
        time.sleep(2)
        
        # Example: each charge row has <tr class="time_timecardtable">
        # with a category name in <td class="time_timecardtableItem">
        categories = []
        charge_rows = self.driver.find_elements(
            By.XPATH,
            "//tr[@class='time_timecardtable'][not(contains(@style, 'background-color'))]"
        )
        
        for row in charge_rows:
            code_cell = row.find_element(By.CLASS_NAME, "time_timecardtableItem")
            code_name = code_cell.text.strip()
            if code_name:
                categories.append(code_name)
        
        return categories

    def submit_hours(self, category, hours, date_str):
        """
        Submits (or edits) 'hours' for 'category' on the *currently open timesheet* 
        for date 'date_str' (YYYY-MM-DD). If there's already a numeric value in that cell:
          - If it matches 'hours', we do NOTHING (skip).
          - Otherwise, we go through the "edit reason" flow.
        """
        if not self.driver:
            self.login()
        
        try:
            # 1) Convert "2025-01-31" to "1/31/2025" (or similar) used in Procas links
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            link_date = dt_obj.strftime("%-m/%-d/%Y")  # on Windows you may need "%#m/%#d/%Y"

            # 2) Find the row for this category
            row_xpath = (
                "//tr[@class='time_timecardtable'][td[@class='time_timecardtableItem']/a[text()='{cat}']]"
            ).format(cat=category)
            row_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, row_xpath))
            )
            
            # 3) Within that row, find the <a> link containing "entrydate=1/31/2025", e.g.
            cell_link_xpath = f".//a[contains(@href, 'entrydate={link_date}')]"
            cell_link_element = WebDriverWait(row_element, 10).until(
                EC.presence_of_element_located((By.XPATH, cell_link_xpath))
            )
            
            cell_text = cell_link_element.text.strip()  # e.g. "" or "8"

            # 4) If the cell_text is numeric, parse it as float
            #    We'll compare it to the new hours so we don't do a pointless edit.
            new_hrs_float = float(hours)
            old_hrs_float = 0.0  # default if blank/spacer
            already_has_value = False

            if cell_text.replace('.', '', 1).isdigit():
                # cell_text is something like "8", "8.0", "2", "4.5"...
                already_has_value = True
                old_hrs_float = float(cell_text)

            # 5) Decide whether to skip, edit, or add
            if already_has_value:
                # There's an existing numeric value in the cell
                if abs(old_hrs_float - new_hrs_float) < 0.000001:
                    # The new value == old value -> skip entirely
                    print(f"Hours match existing value ({old_hrs_float}). Skipping edit.")
                    return
                else:
                    # Edit existing entry
                    self.edit_existing_hours(cell_link_element, old_hrs_float, new_hrs_float)
            else:
                # No existing numeric value -> add new
                self.add_new_hours(cell_link_element, new_hrs_float)

        except Exception as e:
            print(f"Error submitting hours for {category} on {date_str}: {str(e)}")

    def add_new_hours(self, cell_link_element, new_hrs_float):
        """
        If the cell is blank or just a spacer, we go to AddTimeCardHours.aspx,
        fill 'txthrs', and save.
        """
        cell_link_element.click()
        time.sleep(2)
        
        hours_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "txthrs"))
        )
        hours_input.clear()
        hours_input.send_keys(str(new_hrs_float))
        
        # Click save
        save_button = self.driver.find_element(By.ID, "btnsave")
        save_button.click()
        time.sleep(2)

    def edit_existing_hours(self, cell_link_element, old_hrs_float, new_hrs_float):
        """
        When there's already a numeric value in the cell, we edit it as follows:
        
        1) On the main timesheet, click the cell link that shows old hours 
        (leading to listHours.aspx).
        2) On listHours.aspx, click the link (e.g. "8.00") for the existing entry 
        to go to the time entry page.
        3) On the time entry page (AddTimeCardHours.aspx / EditTimeCardHours.aspx),
        clear 'txthrs', type new_hrs_float, and click 'Save'.
        4) Now a reason page appears AFTER saving hours. Fill 
        "Accidentally entered incorrect time" in the reason field and click OK/Submit.
        5) Done.
        """
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException

        # ---------------------------
        # STEP 1) Click the main cell link on the timesheet
        # ---------------------------
        print("Clicking main cell link that shows existing hours...")
        cell_link_element.click()
        time.sleep(2)
        print(f"URL after clicking main cell link: {self.driver.current_url}")

        # ---------------------------
        # STEP 2) On listHours.aspx, find the link matching old_hrs_float
        # ---------------------------
        old_hrs_str = str(int(old_hrs_float))       # e.g. "8"
        old_hrs_str_2dec = f"{old_hrs_float:.2f}"   # e.g. "8.00"
        
        existing_entry_xpath = (
            f"//a[normalize-space(text())='{old_hrs_str}' or normalize-space(text())='{old_hrs_str_2dec}']"
        )
        try:
            existing_entry_link = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, existing_entry_xpath))
            )
        except TimeoutException:
            # Fallback: use "contains" if exact match not found
            fallback_xpath = f"//a[contains(normalize-space(text()), '{int(old_hrs_float)}')]"
            existing_entry_link = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, fallback_xpath))
            )

        print("Clicking existing entry link in listHours.aspx...")
        existing_entry_link.click()
        time.sleep(2)
        print(f"URL after clicking existing hours entry: {self.driver.current_url}")

        # ---------------------------
        # STEP 3) Time Entry Page: fill new hours and click Save
        # (The final table you mentioned: ID=txthrs, ID=btnsave)
        # ---------------------------
        hours_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "txthrs"))
        )
        hours_input.clear()
        hours_input.send_keys(str(new_hrs_float))

        save_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "btnsave"))
        )
        # Scroll into view in case it's off-screen
        self.driver.execute_script("arguments[0].scrollIntoView(true);", save_button)

        try:
            save_button.click()
        except:
            # Fallback JS click
            self.driver.execute_script("arguments[0].click();", save_button)

        time.sleep(2)
        print(f"Clicked Save on final time-entry page. Current URL: {self.driver.current_url}")

        # ---------------------------
        # STEP 4) Reason Page appears AFTER we click Save
        # Fill "Accidentally entered incorrect time" and click OK or Submit
        # ---------------------------
        try:
            reason_input = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "txtreason"))
            )
            reason_input.clear()
            reason_input.send_keys("Accidentally entered incorrect time")
            
            # The button might be "btnreasonok" or "btnsave" or "btnsubmit"
            # Adjust as needed
            reason_ok_xpath = "//*[@id='btnreasonok' or @id='btnsubmit' or @id='btnsave']"
            reason_ok_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, reason_ok_xpath))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", reason_ok_button)
            time.sleep(1)
            reason_ok_button.click()
            time.sleep(2)
            print("Clicked OK on the AFTER-SAVE reason page.")
        except TimeoutException:
            print("No AFTER-SAVE reason page appeared. Continuing...")

        # ---------------------------
        # STEP 5) Done
        # ---------------------------
        print("Finished editing existing hours; new value =", new_hrs_float)




    def cleanup(self):
        """Close the browser when done."""
        if self.driver:
            self.driver.quit()
            self.driver = None
