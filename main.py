import os
import re
from datetime import datetime

def sort_by_timestamp(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        lines = file.readlines()

    # Define a function to extract and convert the timestamp
    def extract_timestamp(line):
        match = re.search(r'\[(.*?)\]', line)
        if match:
            timestamp_str = match.group(1)
            try:
                return datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M')
            except ValueError:
                return None  # Invalid timestamp format
        return None

    # Filter and sort the lines based on the extracted timestamps
    lines_with_timestamps = [line for line in lines if extract_timestamp(line) is not None]
    sorted_lines = sorted(lines_with_timestamps, key=lambda line: extract_timestamp(line))

    sorted_file_path = 'sorted.txt'

    with open(sorted_file_path, 'w', encoding='utf-8', errors='ignore') as sorted_file:
        sorted_file.writelines(sorted_lines)

    return sorted_file_path

filepaths = []

for path, subdirs, files in os.walk('logs'):
    for name in files:
        if name.endswith('.txt'):
            filepaths.append([path, name])

def output(name, sllogs):
    with open(name, 'r', encoding='utf-8', errors='ignore') as file:
        sllogs += file.read() + "\n"
    return sllogs

def remove_duplicates(input_file, output_file):
    lines_seen = set()
    with open(output_file, 'w', encoding='utf-8', errors='ignore') as out_file:
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as in_file:
            for line in in_file:
                if line not in lines_seen:
                    out_file.write(line)
                    lines_seen.add(line)


while len(filepaths) != 0:
    ftr = []
    sllogs = ""
    for fileobj in filepaths:
        file1 = os.path.join(filepaths[0][0], filepaths[0][1]) # Path to file being compared
        fileone = re.sub(r'-\d{4}-\d{2}', '', filepaths[0][1].lower())
        filetwo = re.sub(r'-\d{4}-\d{2}', '', fileobj[1].lower())
        #If folder paths are the same
        if filepaths[0][0] == fileobj[0] and fileone == filetwo:
            sllogs = output(file1, sllogs)
            ftr.append(fileobj)
        # If file names are the same
        elif fileone == filetwo:
            if fileone == filetwo:
                file2 = os.path.join(fileobj[0], fileobj[1]) # Path to file being compared to
                sllogs = output(file2, sllogs)
                ftr.append(fileobj)
    
    with open('output/input.txt', 'w', encoding='utf-8', errors='ignore') as outfile:
        outfile.write(sllogs)
        outfile.close()

    input_file = 'output/input.txt'
    output_file = 'output/' + fileone
    sorted_file_path = sort_by_timestamp(input_file)
    remove_duplicates(sorted_file_path, output_file) 
    
    os.remove("output/input.txt")
    os.remove(sorted_file_path)


    for fo in ftr:
        if fo in filepaths:
            filepaths.remove(fo)



