import os
import re
import sys
import tkinter as tk
from pathlib import Path
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import Locator
from playwright.sync_api import expect

import time
from io import BytesIO
from PIL import Image
import zipfile
from pprint import pprint


SUBDIRECTORY_PREFIX = 'week'
NUMBER_OF_SUBDIRECTORIES = 8
url_prefix = "https://learn.zybooks.com"
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
        print(f"base_path: {self.base_path}  session_path: {self.session_path}   session: {self.session}")

    def run(self):
        # initialize the Playwright browser as a context manager to ensure proper cleanup
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)

            # outer loop for complete session
            try:
                self.context =  browser.new_context()
                self.page = self.context.new_page()
                self.sign_on(self.username, self.password)

                self.find_courses()
                self.select_course()
                # signon is complete, course is selected)

                self.download_report_file([1, 2, 5])

                test_list = ["John Carlos Aguinaldo", "Samuel Agyei", "Dovi Atikpo", "Monty Antonetty",
                             "Da'Von Baker", "Tara Beck", "Darius Coleman", "Colton Connally", "Jacob Corrice",
                             "Kristopher Currier", "Micheal Farris", "Daydee Guerra","Jacquelyn Hall",
                             "Devin Hayes", "Keelan Hoover", "Ethan Horton", "Jay Kenny", "Brandon Kramer", 
                             "Austin Lancaster", "Chase Mihal", "Noemi Perez", "TRAVIS RUSKAMP", 
                             "Ethan Sunday", "Nozima Tuychieva", "akira Tyler", "Michael Urbaschek", 
                             "Demitrus Ware"]
                self.download_lab_files([1], test_list)

                print('*** DONE ***')


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



    # To be implemented later when statistics are added
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
            raise ValueError 
        return username, password
 
    # command line contains complete path name to folder of files
    # last component of path is session name
    def get_paths(self, session_path):
        if session_path in ['', None]:
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
        self.page.wait_for_url("**/zybook/**", timeout=0)

        print(f"Selected course: {self.page.url}")    

  
    def get_chapters_and_sections(
            self,
            chapter_numbers,
            print_results=False
        ):

        toc = self.page.locator(".table-of-contents")

        chapters = toc.locator(
            "li.chapter-item:not(.unused-chapter-item)"
        )

        results = []

        for i in range(chapters.count()):

            chapter_number = i + 1

            # Ignore chapters we don't want.
            if chapter_number not in chapter_numbers:
                continue

            chapter = chapters.nth(i)

            chapter_title = (
                chapter.locator(".chapter-title")
                .inner_text()
                .strip()
            )

            checkbox = chapter.locator(
                'input[type="checkbox"]'
            )

            # Explicitly select this chapter.
            checkbox.set_checked(True)

            # Get actual chapter number from its title.
            chapter_number_text = chapter_title.split(".", 1)[0]

            # Expand chapter if necessary.
            expand_button = chapter.locator(
                'button[aria-expanded="false"]'
            )

            if expand_button.count() > 0:
                expand_button.click()

            section_links = toc.locator(
                f'a.section-title-link'
                f'[href*="/chapter/{chapter_number_text}/section/"]'
            )

            sections = []

            for j in range(section_links.count()):

                link = section_links.nth(j)

                title = (
                    link.locator(".section-title")
                    .inner_text()
                    .strip()
                )
                number = title.split(" ", 1)[0].split(".",1)[1]

                href = link.get_attribute("href")

                sections.append({
                    "number": number,
                    "title": title,
                    "href": href
                })

            results.append({
                "number": chapter_number_text,
                "title": chapter_title,
                "sections": sections
            })

            if print_results:

                print(chapter_title)

                for section in sections:
                    print(f'    {section["title"]}')
                    print(f'        {section["href"]}')

        return results

# -----------------------------------------------------------------------------
# download report files -- main block
# -----------------------------------------------------------------------------
    def download_report_file(self, report_chapters):
        self.page.get_by_role("tab", name="Reporting").click()
        
        # Select requested chapters and collect chapter/section information
        self.chapters_and_sections = self.get_chapters_and_sections(report_chapters)
        
        # Generate and download report
        self.report_file_path = self.generate_score_report()

        # Extract course information from downloaded filename
        self.extract_course_parameters(self.report_file_path.name)
# -----------------------------------------------------------------------------
# download lab files - main block
# -----------------------------------------------------------------------------
        # No need to step through chapter_numbers since iter_lab_urls does that
        # lab_urls completely exhausts the generator before proceeding
    def download_lab_files(self, chapter_numbers: list, student_list: list):
        lab_urls = list(
            self.iter_lab_urls(chapter_numbers)
        )

        results = []

        for relative_url in lab_urls:
            url = url_prefix + relative_url
            print(f"Processing: {url}")

            self.page.goto(url)
            self.open_student_activity()

            chapter_number = self.get_chapter_from_url(url)
            section_number = self.get_section_from_url(url)

            for student_name in student_list:
                print(f"    Selecting student: {student_name}")

                student_row = self.select_student(student_name)
                

                attempts = self.get_attempts(student_row, student_name)
                # print("ATTEMPTS: ", attempts)


                results.append({
                    "chapter": chapter_number,
                    "section": section_number,
                    "url": url,
                    "student": student_name,
                    "attempts": attempts,
                })

                for attempt in attempts:
                    print(
                        f'        {attempt["date"]} '
                        f'{attempt["time"]}: '
                        f'{attempt["score"]} '
                        f'{attempt["program"]}'
                    )



            print(f"    Lab pages for {student_name} have been processed")
        return results                
# -----------------------------------------------------------------------------   
# 
# Phase 1: Locate the selected student row             
    def get_student_row(self, student_name: str):
        normalized_name = " ".join(student_name.split())

        student_rows = self.page.locator(
            ".item-row:visible"
        ).filter(
            has=self.page.locator(".student-review-item")
        )

        for i in range(student_rows.count()):
            row = student_rows.nth(i)
            name_element = row.locator(".student-header")

            if name_element.count() == 0:
                continue

            displayed_name = " ".join(
                name_element.inner_text().split()
            )

            if displayed_name == normalized_name:
                return row

        return None


    def get_selected_student_row(self):
        return self.page.locator(
            ".student-review-item"
        ).filter(
            visible=True
        ).first

    # Phase 2A: Determine whether submissions exist
    def student_has_no_submissions(self, student_row) -> bool:
        return student_row.get_by_text(
            "No submissions",
            exact=True
        ).count() > 0

    # Phase 2B: Expand the student row
    def expand_student_attempts(self, student_row):
        expand_button = student_row.locator(
            'button[aria-controls]'
        )

        if expand_button.count() != 1:
            raise RuntimeError(
                "Expected exactly one student-row expansion button, "
                f"but found {expand_button.count()}."
            )

        print(
            "BEFORE CLICK:",
            expand_button.get_attribute("aria-controls"),
            expand_button.get_attribute("aria-expanded"),
        )

        if expand_button.get_attribute("aria-expanded") == "false":
            expand_button.click()

        expect(expand_button).to_have_attribute(
                "aria-expanded",
                "true",
                timeout=10000,
            )

        print(
            "AFTER CLICK:",
            expand_button.get_attribute("aria-controls"),
            expand_button.get_attribute("aria-expanded"),
        )

        return expand_button.get_attribute("aria-controls")



    # Phase 2C: Find the associated attempt area
    def get_attempt_container(self, student_row, student_name):
        expand_button = student_row.locator(
            'button[aria-controls]'
        )

        if expand_button.count() != 1:
            raise RuntimeError(
                "Could not uniquely identify the student "
                "expansion button."
            )

        if expand_button.get_attribute(
            "aria-expanded"
        ) == "false":

            expand_button.click()

            expect(expand_button).to_have_attribute(
                "aria-expanded",
                "true",
                timeout=10000,
            )

        # The expanded student area is in the item-container
        # immediately following this student's item-row.
        expanded_container = student_row.locator(
            "xpath=following-sibling::div"
            "[contains(@class, 'item-container')][1]"
            "//div[contains(@class, 'item-expanded')]"
        )

        expect(expanded_container).to_be_visible(
            timeout=20000
        )

        # The container can become visible while zyBooks is
        # still loading its contents.
        loading_spinner = expanded_container.locator(
            ".zb-progress-circular"
        )

        expect(loading_spinner).to_be_hidden(
            timeout=20000
        )

        expanded_text = " ".join(
            expanded_container.inner_text().split()
        )

        # print(f"        EXPANDED TEXT for {student_name}: {expanded_text!r}")

        # Legitimate no-attempt states.
        no_attempt_states = (
            "Student has not opened this lab",
            "Student has not submitted this lab",
            )

        if any(
            state in expanded_text
            for state in no_attempt_states
        ):
            return None

        # Normal submissions state.
        expected_heading = (
            f"All submissions for {student_name}"
        )

        if expected_heading in expanded_text:
            return expanded_container

        # Neither known state occurred.
        raise RuntimeError(
            f"Expanded student area for {student_name!r} "
            "did not contain either expected state. "
            f"Text was: {expanded_text!r}"
        )    
    # Phase 2D: Extract attempts
    def get_attempts(self, student_row: str, student_name) -> list:

        if student_row is None:
            raise RuntimeError(
                f"Could not find the row for {student_name!r}."
            )

        top_row = self.page.get_by_role("table")
        attempt_rows = top_row.locator("div.item-row")

        if self.student_has_no_submissions(student_row):
            print(f"        No submissions for {student_name}")
            return []
        

        attempt_container = self.get_attempt_container(
            student_row,
            student_name,
        )

        if attempt_container is None:
            print(
                f"        Student has not submitted this lab: "
                f"{student_name}"
            )
            return []
        

        expect(attempt_rows.first).to_be_visible(
            timeout=20000
        )

        attempts = []

        for i in range(attempt_rows.count()):
            attempt_row = attempt_rows.nth(i)

            fields = attempt_row.locator(
                "span.text-sm.w-24"
            )

            if fields.count() < 3:
                continue

            date = " ".join(
                fields.nth(0).inner_text().split()
            )

            time_value = " ".join(
                fields.nth(1).inner_text().split()
            )

            score = "".join(
                fields.nth(2).inner_text().split()
            )
            
            btn = attempt_row.get_by_role("button")
            btn.click()

            # Container holding the zyBooks test feedback
            feedback_container = self.page.locator('div.mr-4')

            # Wait until it actually exists/appears
            feedback_container.last.wait_for(state="visible")

            # One child element for every zyBooks test in this attempt
            children = feedback_container.locator(":scope > *")

            feedback = []

            if children.count() > 3:
                for i in range(2, children.count()):
                    child = children.nth(i)

                    png = child.screenshot()
                    feedback.append(png)

            program = self.get_program(student_row, student_name)


            attempts.append({
                "date": date,
                "time": time_value,
                "score": score,
                "feedback": feedback,
                "program": program
            })

        return attempts

    def get_program(self, student_row, student_name):
        program_button = self.page.get_by_role("button", name="Open submission's code")
        program_button.click()

        return  self.click_download_element(self.session_path)


    # frame coding from copilot
    def click_download_element(self, destination_folder: str | Path) -> list:
    
        new_files: list[Path] = []
        destination_folder = Path(destination_folder)
        destination_folder.mkdir(parents=True, exist_ok=True)

        # Locate the two sibling iframes.
        iframe_elements = self.page.locator(
            'iframe[title="Code and output"]'
        )

        # Equivalent to waiting until Selenium finds exactly two frames.
        expect(iframe_elements).to_have_count(2, timeout=5_000)

        # Try the frames in reverse order, as in your Selenium code.
        for index in reversed(range(iframe_elements.count())):
            try:
                # Convert this specific iframe element into a FrameLocator.
                frame = iframe_elements.nth(index).content_frame

                download_button = frame.get_by_role(
                    "button",
                    name="Download Project at Timestamp",
                    exact=True
                )

                # Wait for this frame's button to become visible.
                download_button.wait_for(
                    state="visible",
                    timeout=5_000
                )

                # Start listening before performing the download-producing click.
                with self.page.expect_download(timeout=10_000) as download_info:
                    download_button.click(timeout=5_000)

                download = download_info.value

                destination = (
                    destination_folder / download.suggested_filename
                )

                download.save_as(destination)
                new_files.append(destination)

                print(f"Downloaded: {destination}")
                break

            except PlaywrightTimeoutError:
                print(
                    f"Download button not found or download not started "
                    f"in frame {index}"
                )

                # Try the next frame rather than ending the loop.
                continue

        if len(new_files) != 1:
            print("Number of downloaded files is incorrect at ", len(new_files))

        extension = new_files[0].suffix
        if extension.lower() == ".zip":
            new_files = self.unzip_zip_file(str(new_files[0]), self.session_path)
        
        return new_files


    def unzip_zip_file(self, zip_file_path, destination):
        unzipped_files = []
        try:
            with zipfile.ZipFile(zip_file_path) as zipf:
                for member in zipf.namelist():
                    if member.endswith('.py'):
                        zipf.extract(member, destination)
                        new_file_name = Path(os.path.join(destination, member))
                        unzipped_files.append(new_file_name)

                        # old_file_path = normjoin(destination, member)
                        # new_file_path = normjoin(destination, new_file_name)
                        # if os.path.exists(new_file_path):
                        #     os.remove(new_file_path)
                        # os.rename(old_file_path, new_file_path)
            # os.remove((src))
        except zipfile.BadZipFile:
            print("Bad zip file")
        return unzipped_files


# Helper functions ------------------------------------------------------------

    def get_chapter_from_url(self, url: str) -> str:
        match = re.search(r"/chapter/([^/]+)", url)

        if not match:
            raise ValueError(
                f"Chapter number was not found in URL: {url}"
            )

        return match.group(1)


    def get_section_from_url(self, url: str) -> str:
        match = re.search(r"/section/([^/?#]+)", url)

        if not match:
            raise ValueError(
                f"Section number was not found in URL: {url}"
            )

        return match.group(1)

    def wait_for_student_row(
        self,
        student_name: str,
        timeout: float = 20.0,
    ):
        end_time = time.monotonic() + timeout

        block = self.page.locator('//div[@class="list flex flex-col"]').first
        print("WAIT FOR STUDENT ROW")
       
        # Wait for it to exist in the DOM 
        block.wait_for(state="attached", timeout=end_time)
       
        expect(block).not_to_contain_text("Loading", timeout=end_time)
        
        
        pass
       
# -------------------- end ----------------------------------------------------


    def get_student_activity_panel(self):
        return self.page.locator(
            ".zb-card-content"
        ).filter(
            has=self.page.get_by_text(
                "Student activity",
                exact=True,
            )
        )
    def open_student_activity(self):
        panel = self.get_student_activity_panel()

        button = panel.get_by_role("button",
                                   name="Student activity", 
                                   exact=True)

        button.scroll_into_view_if_needed()

        # zyBooks may display its introductory tutorial here.
        self.skip_tutorial_if_present()

        if button.get_attribute("aria-expanded") == "false":
            button.click()
  
       
    def select_student(self, student_name: str) -> Locator:
        panel = self.get_student_activity_panel()
        student_combobox = panel.get_by_role("combobox", name="Students")
        student_combobox.click()


        dropdown = self.page.locator(".ember-power-select-dropdown:visible")
        expect(dropdown).to_be_visible(timeout=20_000)

        
        # Wait for any loading spinner to finish and options to render
        expect(dropdown.locator(".ember-power-select-option--loading-message")).to_be_hidden(timeout=15_000)
        options = dropdown.locator(".ember-power-select-option:not(.ember-power-select-option--loading-message)")
        expect(options.first).to_be_visible(timeout=15_000)
        # print(f"Rendered options count: {options.count()}")


        # Match using word boundaries instead of strict start/end anchors
        matching_option = options.filter(
            has_text=re.compile(rf"\b{re.escape(student_name)}\b", re.IGNORECASE)
        ).first

        matching_option.scroll_into_view_if_needed()
        expect(matching_option).to_be_visible(timeout=5_000)
        self.page.wait_for_timeout(timeout=2_000)

        matching_option.click() 


        row = self.page.locator(".item-row").filter(has_text=student_name)
        row.wait_for(state="visible", timeout=10_000)

        row.click()

        try:
            expect(row).to_contain_text(re.compile(r"min:\d+|No submissions"), timeout=5_000)
        except AssertionError:
            print('TimeoutError: ', ' '.join(row.inner_text().split('\n')))

        return row
        

    def skip_tutorial_if_present(self):
        dialog = self.page.get_by_role("dialog")

        try:
            dialog.wait_for(state="visible", timeout=5000)
            dialog.get_by_role(
                "button",
                name="Skip",
                exact=True
            ).click()

        except PlaywrightTimeoutError:
            # Tutorial did not appear.
            pass
# -----------------------------------------------------------------------------        

    def iter_lab_urls(self, chapter_numbers):
        requested_chapters = {str(n) for n in chapter_numbers}

        toc = self.page.locator(".table-of-contents")

        section_links = toc.locator("a.section-title-link")

        for i in range(section_links.count()):
            link = section_links.nth(i)

            title = (
                link.locator(".section-title")
                .inner_text()
                .strip()
            )

            if "LAB:" not in title:
                continue

            chapter_number = title.split(".", 1)[0]

            if chapter_number in requested_chapters:
                yield link.get_attribute("href")



    def generate_score_report(self) -> Path:

        # Wait for the download to begin when the button is clicked
        with self.page.expect_download() as download_info:

            self.page.get_by_role(
                "button",
                name="Generate score report"
            ).click()

        # Get the Playwright Download object
        download = download_info.value

        # Get the filename supplied by the website
        filename = download.suggested_filename

        # Construct the complete destination path
        destination = Path(self.session_path) / filename

        # check for files with .csv extension
        rename_csv_to_old(self.session_path)

        # Save the file.
        # save_as() waits for the download to complete if necessary.
        download.save_as(destination)

        # print(f"Downloaded: {filename}")
        print(f"Saved to:   {destination}")

        # Return the complete pathname for subsequent processing
        return destination


    # using the report file name, extract pertinent course parameters
    def extract_course_parameters(self, filename):
        try:
            match = re.match(report_file_name_pattern(), str(filename))
            self.course = match.group('course')
            self.term = match.group('term')
            self.session = match.group('session')
            self.as_of = match.group('datetime')
        except Exception as e:
            print('Unable to extract course information from report file name')
            print(filename)
            sys.exit(1)

 
# =============================================================================
    # diagnostic purposes only
    def html_changes(self, page, expression, *args, **kwargs):
        import difflib
        before = page.content()
        expression(*args, **kwargs)
        after = page.content()
        diff = difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile = "before",
            tofile = "after",
            n = 0, 
            lineterm=""
        )
        print("\n".join(diff))
        return

    def show_png(self, png):
        Image.open(BytesIO(png)).show()

    def determine_element_type(self, search_name):
        print("button:", self.page.get_by_role("button", name=search_name).count())

        print("link:", self.page.get_by_role("link", name=search_name).count())

        print("tab:",  self.page.get_by_role("tab", name=search_name).count())

        print("text:", self.page.get_by_text(search_name, exact=True).count())

# Non-class (static) functions
# rename all files in a folder from *.csv to *.old
def rename_csv_to_old(directory: str = ".") -> None:
    folder = Path(directory)
    
    for file_path in folder.glob("*.csv"):
        # file_path.stem gets the filename without the .csv extension
        new_path = file_path.with_name(f"{file_path.stem}.old")
        file_path.rename(new_path)
        print(f"Renamed: {file_path.name} -> {new_path.name}")

def report_file_name_pattern() -> str:
    return r'(?i)^(?P<course>\w{2}-\d{3,4})-(?P<session>\d{4,5})-(?P<term>.*?)_report_\d+_(?P<datetime>\d{4}-\d{2}-\d{2}_\d{4})_e[sd]t\.csv$'
    # file name format for Excel file downloaded from zyBooks. Ex: IT-140-15409-M01_Introduction_to_Scripting_2026_C-2_Jan_-_Mar_report_110587_2026-02-14_1214_est.csv
    # return r"""
    #            (?xi)                                              # verbose and ignore case
    #            ^                                                  # start of line
    #            (P<course>\w{2}-\d{3,4})                           # group named course for IT-140
    #            -                                                  # course-session separator
    #            (P<session>]\d{4,5})                               # group names session for session number 4 or 5 numbers
    #            -                                                  # session-term separator
    #            (P<term>.*?)                                       # group named term unlimited numbere of characters, non greedy (will stop at underscore)
    #            _report_                                           # fixed field
    #            (P<datetime>\d{4}-\d{2}-\d{2}_\d{4}_e[s|d]t        # date-time in yyyy-mm-dd_hhmm e(s or d)t
    #            \.csv                                              # file extension
    #            $                                                  # end of line
    #        """



if __name__ == "__main__":
    cmd_line = sys.argv

    root = tk.Tk()

    server = WebServices(root)

    server.run()