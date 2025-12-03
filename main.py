import os, re, requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from datetime import datetime
from colorama import Fore, Style

class Console:
    def __init__(self) -> None:
        self.colors = {"green": Fore.GREEN, "red": Fore.RED, "yellow": Fore.YELLOW, "blue": Fore.BLUE, "magenta": Fore.MAGENTA, "cyan": Fore.CYAN, "white": Fore.WHITE, "black": Fore.BLACK, "reset": Style.RESET_ALL, "lightblack": Fore.LIGHTBLACK_EX, "lightred": Fore.LIGHTRED_EX, "lightgreen": Fore.LIGHTGREEN_EX, "lightyellow": Fore.LIGHTYELLOW_EX, "lightblue": Fore.LIGHTBLUE_EX, "lightmagenta": Fore.LIGHTMAGENTA_EX, "lightcyan": Fore.LIGHTCYAN_EX, "lightwhite": Fore.LIGHTWHITE_EX}

    def clear(self):
        os.system("cls" if os.name == "nt" else "clear")

    def timestamp(self):
        return datetime.now().strftime("%H:%M:%S")
    
    def success(self, message, obj):
        print(f"{self.colors['lightblack']}{self.timestamp()} » {self.colors['lightgreen']}SUCC {self.colors['lightblack']}• {self.colors['white']}{message} : {self.colors['lightgreen']}{obj}{self.colors['white']} {self.colors['reset']}")

    def error(self, message, obj):
        print(f"{self.colors['lightblack']}{self.timestamp()} » {self.colors['lightred']}ERRR {self.colors['lightblack']}• {self.colors['white']}{message} : {self.colors['lightred']}{obj}{self.colors['white']} {self.colors['reset']}")

    def done(self, message, obj):
        print(f"{self.colors['lightblack']}{self.timestamp()} » {self.colors['lightmagenta']}DONE {self.colors['lightblack']}• {self.colors['white']}{message} : {self.colors['lightmagenta']}{obj}{self.colors['white']} {self.colors['reset']}")

    def warning(self, message, obj):
        print(f"{self.colors['lightblack']}{self.timestamp()} » {self.colors['lightyellow']}WARN {self.colors['lightblack']}• {self.colors['white']}{message} : {self.colors['lightyellow']}{obj}{self.colors['white']} {self.colors['reset']}")

    def info(self, message, obj):
        print(f"{self.colors['lightblack']}{self.timestamp()} » {self.colors['lightblue']}INFO {self.colors['lightblack']}• {self.colors['white']}{message} : {self.colors['lightblue']}{obj}{self.colors['white']} {self.colors['reset']}")

    def custom(self, message, obj, color):
        print(f"{self.colors['lightblack']}{self.timestamp()} » {self.colors[color.upper()]}{color.upper()} {self.colors['lightblack']}• {self.colors['white']}{message} : {self.colors[color.upper()]}{obj}{self.colors['white']} {self.colors['reset']}")

    def input(self, message):
        return input(f"{self.colors['lightblack']}{self.timestamp()} » {self.colors['lightcyan']}INPUT   {self.colors['lightblack']}• {self.colors['white']}{message}{self.colors['reset']}")

log = Console()

class Downloader:
    def __init__(self, download_folder=None, progress_callback=None, log_callback=None):
        self.download_folder = download_folder or os.getcwd()
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        os.makedirs(self.download_folder, exist_ok=True)
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.5',
            'referer': 'https://fitgirl-repacks.site/',
            'sec-ch-ua': '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        }

    def _log(self, type, message, obj=""):
        if self.log_callback:
            self.log_callback(type, message, obj)
        else:
            # Fallback to console logging
            if type == 'info': log.info(message, obj)
            elif type == 'success': log.success(message, obj)
            elif type == 'error': log.error(message, obj)
            elif type == 'warning': log.warning(message, obj)
            elif type == 'done': log.done(message, obj)

    def download_file(self, download_url, output_path):
        response = requests.get(download_url, stream=True)
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded = 0

            with open(output_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    f.write(data)
                    downloaded += len(data)
                    if self.progress_callback:
                        self.progress_callback(downloaded, total_size, output_path)
            
            self._log('success', "Successfully Downloaded File", f"{output_path}")
            return True
        else:
            self._log('error', "Failed To Download File", response.status_code)
            return False

    def process_link(self, link):
        self._log('info', "Started Processing", link)
        try:
            response = requests.get(link, headers=self.headers)
        except Exception as e:
             self._log('error', "Failed To Fetch Page", str(e))
             return

        if response.status_code != 200:
            self._log('error', "Failed To Fetch Page", response.status_code)
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        meta_title = soup.find('meta', attrs={'name': 'title'})
        file_name = meta_title['content'] if meta_title else "default_file_name"
        
        # Sanitize filename
        file_name = "".join([c for c in file_name if c.isalpha() or c.isdigit() or c in (' ', '.', '_', '-')]).rstrip()
        
        script_tags = soup.find_all('script')
        download_function = None
        for script in script_tags:
            if 'function download' in script.text:
                download_function = script.text
                break

        if download_function:
            match = re.search(r'window\.open\(["\'](https?://[^\s"\'\)]+)', download_function)
            if match:
                download_url = match.group(1)
                self._log('info', "Found Download Url", download_url)
                output_path = os.path.join(self.download_folder, file_name)
                try:
                    self.download_file(download_url, output_path)
                except Exception as e:
                    self._log('error', "Failed To Download File", str(e))
            else:
                self._log('error', "No Download Url Found", response.status_code)
        else:
            self._log('error', "Download Function Not Found", response.status_code)

def remove_link(processed_link, input_file='input.txt'):
    if not os.path.exists(input_file): return
    with open(input_file, 'r') as file:
        links = file.readlines()
        
    with open(input_file, 'w') as file:
        for link in links:
            if link.strip() != processed_link:
                file.write(link)

if __name__ == "__main__":
    # CLI Usage
    downloads_folder = "/run/media/ancientai/SSD/Games/black-ops-2"
    downloader = Downloader(download_folder=downloads_folder)
    log.clear()

    if os.path.exists('input.txt'):
        with open('input.txt', 'r') as file:
            links = [line.strip() for line in file if line.strip()]

        for link in links:
            downloader.process_link(link)
            remove_link(link)
    else:
        log.warning("input.txt not found", "")
