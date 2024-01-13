import os
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import requests
import subprocess
import json

requests.packages.urllib3.disable_warnings()  # This disables warnings about SSL certificates.


class GitHubDownloader:
    def __init__(self, hostname, owner, repo, branch, token="", path="", folder=""):
        self.hostname = hostname
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.token = token
        self.path = path
        self.folder = folder
        self.failed_download = []

    def get_lfs_file(self, download_file_path, sha, size):
        # Step 1: Create JSON object
        json_data = {
            "operation": "download",
            "transfer": ["basic"],
            "objects": [{"oid": sha, "size": size}]
        }

        # Step 2: Convert JSON to string
        json_str = json.dumps(json_data)

        # Step 3: Make a POST request to LFS API
        headers = {
            "Accept": "application/vnd.git-lfs+json",
            "Content-type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        lfs_api_url = f'https://{self.hostname}/{self.owner}/{self.repo}.git/info/lfs/objects/batch'
        response = requests.post(lfs_api_url, headers=headers, data=json_str)

        if response.status_code != 200:
            # print(f"Failed to download LFS file '{download_file_path}'. Status Code: {response.status_code}")
            # messagebox.showinfo("Download Failed", f"Failed to download text file '{download_file_path}'. Status
            # Code: {response.status_code}")
            self.failed_download.append(
                f"Failed to download text file '{download_file_path}'. Status Code: {response.status_code}")
            return

        # Step 4: Get the download URL from the response
        download_url = response.json()["objects"][0]["actions"]["download"]["href"]
        RemoteAuth = response.json()["objects"][0]["actions"]["download"]["header"]["Authorization"]
        # print(response.json())
        # print(download_url)
        # print(RemoteAuth)

        # Step 5: Download the file
        headers = {
            'Authorization': RemoteAuth
        }

        response = requests.get(download_url, headers=headers)

        if response.status_code == 200:
            with open(download_file_path, 'wb') as f:
                f.write(response.content)
            # Show success message
            # messagebox.showinfo("Download Successful", f"File '{download_file_path}' downloaded successfully.")
        else:
            # print(f"Failed to download LFS file '{download_file_path}'. Status Code: {response.status_code}")
            # messagebox.showinfo("Download Failed", f"Failed to download text file '{download_file_path}'. Status
            # Code: {response.status_code}")
            self.failed_download.append(
                f"Failed to download LFS file '{download_file_path}'. Status Code: {response.status_code}")

    def download_file_from_private_repo(self, file_path, output_path):
        # Construct the raw GitHub URL for the file
        raw_url = f"https://{self.hostname}/raw/{self.owner}/{self.repo}/{self.branch}/{file_path}"
        # Set up the headers with the authorization token
        headers = {"Authorization": f"token {self.token}"}

        # Send a GET request to download the file
        response = requests.get(raw_url, headers=headers)
        # print(response.content)

        # Check if the request was successful
        if response.status_code == 200:
            # Save the content of the response to the output file
            if b'version https://git-lfs.github.com/spec/v1' in response.content:
                response_txt = response.content.decode('utf-8')
                lines = response_txt.strip().split('\n')
                sha = lines[1].split(':')[1]
                size = int(lines[2].split()[1])
                # print(sha)
                # print(size)
                self.get_lfs_file(
                    download_file_path=output_path,
                    sha=sha,
                    size=size
                )
            else:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                # print(f"File '{file_path}' downloaded and saved to '{output_path}'")
                # Show success message
                # messagebox.showinfo("Download Successful", f"File '{file_path}' downloaded successfully.")
        else:
            data = self.get_github_contents(file_path)
            # Construct the raw GitHub URL for the file
            download_url = data['download_url']
            # Set up the headers with the authorization token
            # headers = {"Authorization": f"token {self.token}"}

            # Send a GET request to download the file
            response = requests.get(download_url, verify=False)
            # print(response.content)

            # Check if the request was successful
            if response.status_code == 200:
                # Save the content of the response to the output file
                if b'version https://git-lfs.github.com/spec/v1' in response.content:
                    response_txt = response.content.decode('utf-8')
                    lines = response_txt.strip().split('\n')
                    sha = lines[1].split(':')[1]
                    size = int(lines[2].split()[1])
                    # print(sha)
                    # print(size)
                    self.get_lfs_file(
                        download_file_path=output_path,
                        sha=sha,
                        size=size
                    )
                else:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    # print(f"File '{file_path}' downloaded and saved to '{output_path}'")
                    # Show success message
                    # messagebox.showinfo("Download Successful", f"File '{file_path}' downloaded successfully.")
            else:
                # print(f"Failed to download text file '{file_path}'. Status Code: {response.status_code}")
                # messagebox.showinfo("Download Failed", f"Failed to download text file '{file_path}'. Status Code: {
                # response.status_code}")
                self.failed_download.append(
                    f"Failed to download text file '{file_path}'. Status Code: {response.status_code}")

    def get_github_contents(self, path):
        url = f"https://{self.hostname}/api/v3/repos/{self.owner}/{self.repo}/contents/{path}?ref={self.branch}"
        headers = {"Authorization": f"token {self.token}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            response.raise_for_status()
            return response.json()
        else:
            try:
                url_public_repo = f"https://api.{self.hostname}/repos/{self.owner}/{self.repo}/contents/{path}?ref={self.branch}"
                # headers = {"Authorization": f"token {self.token}"}
                response_public = requests.get(url_public_repo, verify=False)
                # response_public.raise_for_status()
                if response_public.status_code == 200:
                    return response_public.json()
            except requests.exceptions.ConnectionError as e:
                public_org_url = f"https://{self.hostname}/api/v3/repos/{self.owner}/{self.repo}/contents/{path}?ref={self.branch}"
                response_org_public = requests.get(public_org_url, verify=False)
                return response_org_public.json()

    def repo_traversal(self, path, folder):
        data = self.get_github_contents(path)
        for item in data:
            # base case
            if item['type'] == 'file':
                # print(item['name'])
                sublocal_file_path = f"{folder}/{item['name']}"
                self.download_file_from_private_repo(item['path'], sublocal_file_path)
            else:
                sublocal_path = f"{folder}/{item['name']}"

                # Create the local subfolder if it doesn't exist
                if not os.path.exists(sublocal_path):
                    os.makedirs(sublocal_path)
                self.repo_traversal(item['path'], sublocal_path)


class GitHubGUI:
    def __init__(self):
        self.terminate = True
        self.complete_button = None
        self.downloader = None
        self.root = tk.Tk()
        self.root.title("GitHub Auto Resynchronization Tool")

        script_dir = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(script_dir, 'github_git_icon_145985.ico')
        self.root.iconbitmap(icon_path)
        style = ttk.Style()
        style.map("C.TButton",
                  foreground=[('pressed', 'red'), ('active', 'blue')],
                  background=[('pressed', '!disabled', 'black'), ('active', 'white')]
                  )
        ttk.Style().configure("G.TButton", padding=2, relief="flat",
                              background="#00cc0c", foreground="#00cc0c")
        ttk.Style().configure("R.TButton", padding=2, relief="flat",
                              background="#cc0c00", foreground="#cc0c00")

        self.entry_width = 45

        self.entries = []

        self.first_entry = ()

        self.index = 0

        self.cnt = 0

        self.download_failed = []

        self.hostname_entry = None  # ttk.Entry(self.root, width=self.entry_width)
        self.owner_entry = None  # ttk.Entry(self.root, width=self.entry_width)
        self.repo_entry = None  # ttk.Entry(self.root, width=self.entry_width)
        self.token_entry = ttk.Entry(self.root, width=self.entry_width, show="*")

        self.tag_var = None  # tk.StringVar(self.root)

        self.file_path_entry = None  # ttk.Entry(self.root, width=self.entry_width)
        self.output_path_entry = ttk.Entry(self.root, width=self.entry_width)
        self.link_entry = ttk.Entry(self.root, width=self.entry_width)
        self.create_widgets()
        self.create_widgets()

    def export_entries(self):
        # Get the data from the entries and convert it to a list of dictionaries
        entries_data = []
        (link, output_path) = self.first_entry
        if len(self.token_entry.get()) > 0:
            entries_data.append({
                'GitHub Link': link.get(),
                'Output Path': output_path.get(),
                'GitHub Token': self.token_entry.get()  # Include the GitHub Token
            })
        else:
            entries_data.append({
                'GitHub Link': link.get(),
                'Output Path': output_path.get()
            })
        for entry in self.entries:
            link, output_path = entry
            entries_data.append({
                'GitHub Link': link.get(),
                'Output Path': output_path.get()
            })
        filetypes = [("Files with matching extension", "*json")]
        selected_path = filedialog.askopenfilename(filetypes=filetypes, title="Select a json File")
        if selected_path:
            # Save the data to a JSON file
            with open(selected_path, 'w') as json_file:
                json.dump(entries_data, json_file, indent=2)

    def import_entries(self):
        # Load data from the JSON file
        filetypes = [("Files with matching extension", "*json")]
        selected_path = filedialog.askopenfilename(filetypes=filetypes, title="Select a json File")
        if selected_path:
            with open(selected_path, 'r') as json_file:
                entries_data = json.load(json_file)

        # Populate the GUI with the imported entries
        cnt = 0
        for data in entries_data:
            if cnt == 0:
                # Include the GitHub Token in the imported data
                github_token = data.get('GitHub Token', '')
                if github_token:
                    self.token_entry.insert(0, data['GitHub Token'])
            if self.cnt == 0:
                (link_entry, output_path_entry) = self.first_entry
                self.cnt += 1

            else:
                link_entry = ttk.Entry(self.root, width=self.entry_width)
                output_path_entry = ttk.Entry(self.root, width=self.entry_width)

                row_number = len(self.entries) + 3
                link_entry.grid(row=row_number, column=0, padx=5, pady=5, sticky="w")
                output_path_entry.grid(row=row_number, column=1, padx=5, pady=5, sticky="w")

                # link_entry.insert(0, data['GitHub Link'])
                # output_path_entry.insert(0, data['Output Path'])

                ttk.Button(self.root, text="Browse", command=lambda i=output_path_entry: self.browse_output_path(i)).grid(
                    row=row_number, column=2, padx=5, pady=5, sticky="w")
                # Remove the existing "GitHub Token" label and entry
                github_token_label_row = row_number + 1
                github_token_label_col = 0
                self.root.grid_slaves(row=github_token_label_row, column=github_token_label_col)[0].grid_remove()
                if len(self.root.grid_slaves(row=github_token_label_row, column=github_token_label_col)) > 0:
                    self.root.grid_slaves(row=github_token_label_row, column=github_token_label_col)[0].grid_remove()

                github_token_entry_col = 1
                self.root.grid_slaves(row=github_token_label_row, column=github_token_entry_col)[0].grid_remove()

                # Remove the existing "Download" button
                download_button_row = row_number + 2
                download_button_col = 1
                self.root.grid_slaves(row=download_button_row, column=download_button_col)[0].grid_remove()
                if len(self.root.grid_slaves(row=download_button_row, column=download_button_col)) > 0:
                    self.root.grid_slaves(row=download_button_row, column=download_button_col)[0].grid_remove()
                # Remove the existing "+ Add Row" button
                add_row_button_row = row_number
                add_row_button_col = 0
                self.root.grid_slaves(row=add_row_button_row, column=add_row_button_col)[1].grid_remove()
                if len(self.root.grid_slaves(row=add_row_button_row, column=add_row_button_col)) > 1:
                    self.root.grid_slaves(row=add_row_button_row, column=add_row_button_col)[1].grid_remove()

                # Update the list of entries (assuming it's an attribute in your class)
                self.entries.append((link_entry, output_path_entry))

                # Move the "GitHub Token" label and entry to the new position
                github_token_label = ttk.Label(self.root, text="GitHub personal access token:")
                github_token_label.grid(row=row_number + 2, column=0, padx=5, pady=5, sticky="w")

                github_token_entry = ttk.Entry(self.root, width=self.entry_width, show="*")
                github_token_entry.grid(row=row_number + 2, column=1, padx=5, pady=5, sticky="w")
                if len(self.token_entry.get()) > 0:
                    github_token_entry.insert(0, self.token_entry.get())
                self.token_entry = github_token_entry

                # Move the buttons to the next row
                ttk.Button(self.root, text="+ Add Row", command=self.add_row, style="G.TButton").grid(row=row_number + 1,
                                                                                                      column=0, pady=10,
                                                                                                      columnspan=2)
                ttk.Button(self.root, text="Download", command=self.download_file, style="C.TButton").grid(
                    row=row_number + 3,
                    column=0,
                    columnspan=2,
                    pady=10)
            link_entry.insert(0, data['GitHub Link'])
            output_path_entry.insert(0, data['Output Path'])

    def get_info_from_link_by_spliting(self, github_link):
        # github_link = self.link_entry.get()
        # Extracting information from the GitHub link
        parts = github_link.split("/")
        if len(parts) < 5:
            self.terminate = False
            self.download_failed.append(f"Invalid GitHub url: {github_link}")
            return
        # self.hostname_entry.delete(0, tk.END)
        self.hostname_entry = parts[2]
        # self.owner_entry.delete(0, tk.END)
        self.owner_entry = parts[3]
        # self.repo_entry.delete(0, tk.END)
        self.repo_entry = parts[4]
        # self.token_entry.delete(0, tk.END)  # Assuming you don't want to populate the token from the link
        url = f"https://{parts[2]}/{parts[3]}/{parts[4]}"
        all_tags = self.list_all_tags_for_remote_git_repo(url)
        all_branches = self.list_all_branches_for_remote_git_repo(url)
        all_tags += all_branches
        # If user enters GitHub repository page then we will assume that user wants to download main/master branch
        if len(parts) == 5:
            parts.append("tree")
            if "master" in all_tags:
                parts.append("master")
            elif "main" in all_tags:
                parts.append("main")
            else:
                parts.append(all_tags[0])
        # Find the index where "blob" or "tree" occurs
        try:
            tag_index = parts.index("blob") + 1  # For files
        except ValueError:
            try:
                tag_index = parts.index("tree") + 1  # For folders
            except ValueError:
                tag_index = 6  # Not found default value
        # Iterate through all tags and branches to find the one present in the link
        tag_from_link = None
        for tag in all_tags:
            tag_parts = tag.split("/")
            if tag_parts and tag_parts == parts[tag_index:len(tag_parts) + tag_index]:
                tag_from_link = tag
                break

        # Set the tag in the tag_var
        if tag_from_link:
            self.tag_var = tag_from_link
        else:
            # messagebox.showinfo("Invalid Tag/Branch")
            self.terminate = False
            self.download_failed.append(f"Invalid GitHub url: {github_link}")
            return

        # tag_branch_value = "/".join(parts[6:9])
        # self.tag_var.set(tag_branch_value)
        remaining_path = "/".join(parts[len(tag_from_link.split("/")) + tag_index:])
        # self.file_path_entry.delete(0, tk.END)
        self.file_path_entry = remaining_path

    def add_row(self):
        # Create new entries for the new row
        link_entry = ttk.Entry(self.root, width=self.entry_width)
        output_path_entry = ttk.Entry(self.root, width=self.entry_width)

        # Place the new entries in the grid
        row_number = len(self.entries) + 3
        link_entry.grid(row=row_number, column=0, padx=5, pady=5, sticky="w")
        output_path_entry.grid(row=row_number, column=1, padx=5, pady=5, sticky="w")
        self.index = len(self.entries) + 1
        # ttk.Button(self.root, text="Browse", command=self.browse_output_path(output_path_entry)).grid(
        # row=row_number, column=2, padx=5, pady=5, sticky="w")
        ttk.Button(self.root, text="Browse", command=lambda i=output_path_entry: self.browse_output_path(i)).grid(
            row=row_number, column=2, padx=5, pady=5, sticky="w")
        # Remove the existing "GitHub Token" label and entry
        github_token_label_row = row_number + 1
        github_token_label_col = 0
        self.root.grid_slaves(row=github_token_label_row, column=github_token_label_col)[0].grid_remove()
        if len(self.root.grid_slaves(row=github_token_label_row, column=github_token_label_col)) > 0:
            self.root.grid_slaves(row=github_token_label_row, column=github_token_label_col)[0].grid_remove()

        github_token_entry_col = 1
        self.root.grid_slaves(row=github_token_label_row, column=github_token_entry_col)[0].grid_remove()

        # Remove the existing "Download" button
        download_button_row = row_number + 2
        download_button_col = 1
        self.root.grid_slaves(row=download_button_row, column=download_button_col)[0].grid_remove()
        if len(self.root.grid_slaves(row=download_button_row, column=download_button_col)) > 0:
            self.root.grid_slaves(row=download_button_row, column=download_button_col)[0].grid_remove()
        # Remove the existing "+ Add Row" button
        add_row_button_row = row_number
        add_row_button_col = 0
        self.root.grid_slaves(row=add_row_button_row, column=add_row_button_col)[1].grid_remove()
        if len(self.root.grid_slaves(row=add_row_button_row, column=add_row_button_col)) > 1:
            self.root.grid_slaves(row=add_row_button_row, column=add_row_button_col)[1].grid_remove()

        # Update the list of entries (assuming it's an attribute in your class)
        self.entries.append((link_entry, output_path_entry))

        # Move the "GitHub Token" label and entry to the new position
        github_token_label = ttk.Label(self.root, text="GitHub personal access token:")
        github_token_label.grid(row=row_number + 2, column=0, padx=5, pady=5, sticky="w")

        github_token_entry = ttk.Entry(self.root, width=self.entry_width, show="*")
        github_token_entry.grid(row=row_number + 2, column=1, padx=5, pady=5, sticky="w")
        if len(self.token_entry.get()) > 0:
            github_token_entry.insert(0, self.token_entry.get())
        self.token_entry = github_token_entry

        # Move the buttons to the next row
        ttk.Button(self.root, text="+ Add Row", command=self.add_row, style="G.TButton").grid(row=row_number + 1,
                                                                                              column=0, pady=10,
                                                                                              columnspan=2)
        ttk.Button(self.root, text="Download", command=self.download_file, style="C.TButton").grid(row=row_number + 3,
                                                                                                   column=0,
                                                                                                   columnspan=2,
                                                                                                   pady=10)

    def create_widgets(self):
        # Export Button
        ttk.Button(self.root, text="Export", command=self.export_entries).grid(row=0, column=0,
                                                                               columnspan=1, pady=10)
        # Import Button
        ttk.Button(self.root, text="Import", command=self.import_entries).grid(row=0, column=1,
                                                                               columnspan=1, pady=10)
        # Header Row
        ttk.Label(self.root, text="GitHub Link:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(self.root, text="Output Path:").grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # First Row
        link_entry = ttk.Entry(self.root, width=self.entry_width)
        link_entry.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        # self.link_entry.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        # self.output_path_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        output_path_entry = ttk.Entry(self.root, width=self.entry_width)
        output_path_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        # self.entries.append((link_entry, output_path_entry))
        # ttk.Button(self.root, text="Browse", command=self.browse_output_path(output_path_entry)).grid(row=1, column=2,
        #                                                                                               padx=5, pady=5,
        #                                                                                               sticky="w")
        ttk.Button(self.root, text="Browse", command=lambda i=output_path_entry: self.browse_output_path(i)).grid(
            row=2, column=2, padx=5, pady=5, sticky="w")
        # self.entries.append((link_entry, output_path_entry))
        self.first_entry = (link_entry, output_path_entry)

        # Add Row Button
        ttk.Button(self.root, text="+ Add Row", command=self.add_row, style="G.TButton").grid(row=3, column=0, pady=10,
                                                                                              columnspan=2)

        # GitHub Token and Download Button
        ttk.Label(self.root, text="GitHub personal access token:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.token_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")

        ttk.Button(self.root, text="Download", command=self.download_file, style="C.TButton").grid(row=5, column=0,
                                                                                                   columnspan=2,
                                                                                                   pady=10)

        self.root.quit()

    def list_all_tags_for_remote_git_repo(self, url):
        """
            Given a repository URL, list all tags for that repository
            without cloning it.

            This function use "git ls-remote", so the
            "git" command line program must be available.
            """
        # Run the 'git' command to fetch and list remote tags
        result = subprocess.run([
            "git", "ls-remote", "--tags", url
        ], stdout=subprocess.PIPE, text=True)

        # Process the output to extract tag names
        output_lines = result.stdout.splitlines()
        tags = [
            line.split("refs/tags/")[-1] for line in output_lines
            if "refs/tags/" in line and "^{}" not in line
        ]

        return tags

    def list_all_branches_for_remote_git_repo(self, url):
        """
            Given a repository URL, list all branches for that repository
            without cloning it.

            This function uses "git ls-remote", so the
            "git" command line program must be available.
            """
        result = subprocess.run([
            "git", "ls-remote", "--heads", url
        ], stdout=subprocess.PIPE, text=True)

        output_lines = result.stdout.splitlines()
        branches = [
            line.split("refs/heads/")[-1] for line in output_lines
            if "refs/heads/" in line
        ]

        return branches

    def download_file(self):
        self.entries.insert(0, self.first_entry)
        row_number = 2
        no_of_fail = []
        for entries in self.entries:
            self.terminate = True
            (GitHub_link_entry, self.output_path_entry) = entries
            self.get_info_from_link_by_spliting(GitHub_link_entry.get())
            if self.terminate:
                github_token = self.token_entry.get()
                output_path = self.output_path_entry.get()
                self.downloader = GitHubDownloader(self.hostname_entry, self.owner_entry, self.repo_entry, self.tag_var,
                                                   github_token, self.file_path_entry,
                                                   output_path)
                file_extension = os.path.splitext(self.file_path_entry)[-1]
                self.complete_button = ttk.Button(self.root, text="Completed", state="active", style="G.TButton")
                self.complete_button.grid(row=row_number, column=3, columnspan=2, pady=10)
                self.complete_button["state"] = "normal"
                if file_extension:
                    file_name_with_extension = os.path.basename(self.file_path_entry)
                    output_path = f"{output_path}/{file_name_with_extension}"
                    # if not os.path.exists(output_path):
                    #     os.makedirs(output_path)
                    self.downloader.download_file_from_private_repo(self.file_path_entry, output_path)
                    # messagebox.showinfo("Download Successful", f"File '{output_path}' downloaded successfully.")
                    if len(self.download_failed) + len(self.downloader.failed_download) <= len(no_of_fail):
                        self.complete_button.configure(style="G.TButton")
                    else:
                        self.complete_button.configure(style="R.TButton")

                else:
                    folder_name = self.file_path_entry.split('/')[-1]
                    # For Cloning the whole repo file_path = ""
                    # If you want to create all the files/folder inside folder name = repository(exactly like cloning)
                    # Then uncomment below line
                    # folder_name = repository
                    sublocal_path = f"{output_path}/{folder_name}"
                    if not os.path.exists(sublocal_path):
                        os.makedirs(sublocal_path)
                    self.downloader.repo_traversal(self.file_path_entry, sublocal_path)
                    # messagebox.showinfo("Download Successful", f"Folder '{sublocal_path}' downloaded
                    # successfully.")
                    if len(self.download_failed) + len(self.downloader.failed_download) <= len(no_of_fail):
                        self.complete_button.configure(style="G.TButton")
                    else:
                        self.complete_button.configure(style="R.TButton")
                no_of_fail = self.download_failed + self.downloader.failed_download
            else:
                no_of_fail = self.download_failed
                self.complete_button = ttk.Button(self.root, text="Failed", state="active", style="R.TButton")
                self.complete_button.grid(row=row_number, column=3, columnspan=2, pady=10)
                self.complete_button["state"] = "normal"
            # Update the GUI
            self.root.update()
            # Simulate a delay
            # self.root.after(1000)
            row_number += 1
        if len(no_of_fail) > 0:
            msg = ""
            for i in no_of_fail:
                msg += i + "\n"
            messagebox.showinfo("Download Failed", msg)
        else:
            messagebox.showinfo("Download Successful", f"All files are downloaded and saved successfully.")
        self.root.quit()

    def browse_output_path(self, output_path_entry):

        selected_path = filedialog.askdirectory(title="Select Folder")

        if selected_path:
            output_path_entry.delete(self.index, tk.END)
            output_path_entry.insert(self.index, selected_path)
            # self.index += 1

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    gui = GitHubGUI()
    gui.run()
