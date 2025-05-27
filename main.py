import subprocess
import os
from flask import Flask, send_from_directory, jsonify, abort, render_template_string

app = Flask(__name__, static_folder='.')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/run-faces')
def run_faces():
    print("Running detected_faces_viewer.py")
    try:
        # Run your python script and capture output
        subprocess.Popen(['python', 'detected_faces_viewer.py'])
        return jsonify({'output': "Running detected_faces_viewer.py in background"})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': e.stderr}), 500
    
@app.route('/run-poses')
def run_poses():
    print("Running poses_viewer.py")
    try:
        # Run your python script and capture output
        subprocess.Popen(['python', 'poses_viewer.py'])
        return jsonify({'output': "Running poses_viewer.py in background"})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': e.stderr}), 500

@app.route('/ratio/')
def ratio_index():
    folder = 'ratio'
    try:
        files = os.listdir(folder)
    except FileNotFoundError:
        abort(404)

    # Filter only .json files
    json_files = [f for f in files if f.endswith('.json')]

    # Return a simple HTML directory listing with links (like http.server)
    html = '<html><body><h1>Index of /ratio/</h1><ul>'
    for filename in json_files:
        html += f'<li><a href="{filename}">{filename}</a></li>'
    html += '</ul></body></html>'

    return html

@app.route('/details/')
def details_index():
    folder = 'details'
    try:
        files = os.listdir(folder)
    except FileNotFoundError:
        abort(404)

    json_files = [f for f in files if f.endswith('.json')]

    html = '<html><body><h1>Index of /details/</h1><ul>'
    for filename in json_files:
        html += f'<li><a href="{filename}">{filename}</a></li>'
    html += '</ul></body></html>'

    return html

# Static file serving as before
@app.route('/ratio/<path:filename>')
def serve_ratio(filename):
    return send_from_directory('ratio', filename)

@app.route('/details/<path:filename>')
def serve_details(filename):
    return send_from_directory('details', filename)

@app.route('/<path:filename>')
def serve_files(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
