import argparse
import json
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts special characters in a json file')
    parser.add_argument('--input_json_file_path', '-i', required=True, help='JSON file with special characters')
    parser.add_argument('--output_json_file_path', '-o', required=True, help='JSON file with special characters')
    args = parser.parse_args()

    assert os.path.exists(args.input_json_file_path), 'JSON file does not exist!'

    data = None
    with open(args.input_json_file_path, 'r') as inFile:
        data = json.loads(inFile.read())

    assert data, 'Unable to load JSON data!'

    with open(args.output_json_file_path, 'w') as outfile:
        json.dump(data, outfile, indent=2)

    print('Conversion Finished!')
