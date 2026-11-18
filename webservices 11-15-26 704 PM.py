

import os
import re
import sys
import tkinter as tk
from pathlib import Path
from playwright.sync_api import sync_playwright


SUBDIRECTORY_PREFIX = 'week'
NUMBER_OF_SUBDIRECTORIES = 8
signon_page = "https://learn.zybooks.com/signin"


class WebServices(object):
    def __init__(
                self,
                root : tk,
                username : str = None, 
                password : str = None,
                session_path : str = None,
                
                # timeouts
                page_load_timeout : int = 10,
                default_timeout : int = 120,
                # paths               
            ):
        

        # make local copies of parameters passed
        self.root = root
        self.cmd_line = sys.argv

        # determine if username and password are passed in or not
        self.username, self.password = self.get_signon_credentials(username, password)

        self.base_path, self.session_path, self.session =self.get_paths(session_path)
        print(f"\nbase_path: {self.base_path}  session_path: {self.session_path}   session: {self.session}")

        self.page_load_timeout = page_load_timeout
        self.default_timeout = default_timeout
        
        # build paths
        self.download_path = self.get_download_path()  

        # define and initialize counters
        self.initialize_counters()

        # verify the directory structure is in place and subfolders are created if necessary
        if not self.verify_directory_structure(self.session_path):
            print('Directory structure verification failed. Exiting program.')
            sys.exit(1)

        # TODO Formalize parameter summary and print to console
        print("End of __init__()")
        print(f"username: {self.username}  password: {self.password}")
        print(f"base_path: {self.base_path}")
        print(f"base_path: {self.base_path}  session_path: {self.session_path}   session: {self.session}")

    def run(self):
        # initialize the Playwright browser as a context manager to ensure proper cleanup
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)

            # outer loop for complete session
            try:
                self.page = browser.new_page()
                self.sign_on(self.username, self.password)

                self.find_courses()
                self.select_course()
                # signon is complete, course is selected)

                self.download_report_file(['1','2','3'])


            # TODO verify session matches

            # TODO Generate Report File
            # TODO  Determine chapters per module
            # TODO  extract course information -- term, course, session
            # TODO  Click on reporting tab
            # TODO  Select appropriate chapters
            # TODO  Click to generate report
            # TODO  Generate student list from report file
            # TODO  Download report
            # TODO  Generate lab list from report file
            # TODO For each chapter to be processd:
            # TODO  Load appropriate lab page
            # TODO  Clear advanced zybooks modal
            # TODO  Extract attmmpts for this lab for specific student
            # TODO  For each attempt for a student
            # TODO   Download lab taxt
            # TODO   Download zyBooks feedback
            # TODO  Generate participation list from report file

            # TODO verify directory structure for session_path and create if necessary
            
            # TODO Read student list
            # TODO Function without having to read report file.

            finally:
                browser.close() 



    def initialize_counters(self):
        self.tally_students = 0
        self.tally_report_files = 0
        self.tally_lab_files = 0
        self.tally_programs = 0
        self.tally_attempts = 0

    # get signon_credentials from command line or from parameters passed in
    def get_signon_credentials(self, username, password):
        if username in ['', None]:
            username = self.cmd_line[2] if len(self.cmd_line) > 2 else ''
        if password in ['', None]:
            password = self.cmd_line[3] if len(self.cmd_line) > 3 else ''
        if  username in ['', None] or password in ['', None]:
            print("Error: username and password must be provided either as command line arguments or as parameters to the WebServices class.")
            sys.exit(1) 
        return username, password
 
    # command line contains complete path name to folder of files
    # last component of path is session name
    def get_paths(self, session_path):
        if session_path or session_path in ['', None]:
            session_path = sys.argv[1] if len(sys.argv) > 1 else ''
        else:
            session_path = session_path
        path_obj = Path(session_path)

        # get last folder in path
        session = path_obj.name
        # get everything else
        base_path = path_obj.parent
        return base_path, session_path, session


    # get the path to the default system downloads folder
    # Note: 
    def get_download_path(self):
        return Path.home()    

    # verify directory structure for session_path and create if necessary
    def verify_directory_structure(self, session_path)  -> bool:
        base = Path(session_path)   

        try:
                
            # create top level directory is it doesn't exist
            if not base.exists():
                print(f"Creating directory: {base}")
                base.mkdir(parents=True, exist_ok=True)

            # create subdirectories if they don't exist
            for i in range(1, NUMBER_OF_SUBDIRECTORIES + 1):
                subdirectory = base / f"{SUBDIRECTORY_PREFIX} {i}"
                if not subdirectory.exists():
                    print(f"Creating directory: {subdirectory}")
                    subdirectory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directory structure: {e}")
            return False

    def dismiss_cookie_notice(self):
        button = self.page.get_by_role("button", name="Deny Non-Essential")
        if button.count() > 0:
            button.click()
            print("Cookie notice dismissed.")

    def sign_on(self, username, password):

        self.page.goto(signon_page)

        self.dismiss_cookie_notice()

        self.page.locator('input[type="email"]').fill(username)
        self.page.locator('input[type="password"]').fill(password)

        self.page.get_by_role("button", name="Sign in").click()

        # Wait until the active zyBooks container actually appears
        self.page.locator(
            '[data-test-active-zybooks-container]'
        ).wait_for(state="visible")

    def find_courses(self):
        container = self.page.locator('[data-test-active-zybooks-container]')

        courses = container.get_by_role("listitem")

        # Wait until at least the first course is visible
        courses.first.wait_for(state="visible")

        print("Courses found:", courses.count())


        for i in range(courses.count()):
            course = courses.nth(i)
            
            link = course.locator('a')
            href = link.get_attribute('href')
            print(i, href)

    def  select_course(self):

        courses = self.page.locator(
            '[data-test-active-zybooks-container]'
        ).get_by_role("listitem")

        # Wait for course selection screen to become usable
        courses.first.wait_for(state="visible")

        print("Waiting for user to select a course...")

        # Wait indefinitely for user's selection
        self.page.wait_for_url(
            "**/zybook/**",
            timeout=0
        )

        print(f"Selected course: {self.page.url}")    

    def download_report_file(self, report_chapters):
        self.page.get_by_role("tab", name="Reporting").click()


        pass



if __name__ == "__main__":
    cmd_line = sys.argv

    root = tk.Tk()

    server = WebServices(root)
    server.run()