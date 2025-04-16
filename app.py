from multiprocessing import process
import subprocess
from pathlib import Path
from flask import Flask, request, jsonify
import os
from utils.question_matching import find_similar_question
from utils.file_process import unzip_folder
from utils.function_definations_llm import function_definitions_objects_llm
from utils.openai_api import extract_parameters
from utils.solution_functions import functions_dict

tmp_dir = "tmp_uploads"
os.makedirs(tmp_dir, exist_ok=True)

app = Flask(__name__)


SECRET_PASSWORD = os.getenv("SECRET_PASSWORD")


@app.route("/api", methods=["POST"])
def process_file():
    question = request.form.get("question")
    file = request.files.get("file")  # Get the uploaded file (optional)
    file_names = []

    # Ensure tmp_dir is always assigned
    tmp_dir = None
    try:
        matched_function, matched_description = find_similar_question(question)

        if file:
            base_tmp_dir = Path("./tmp_uploads")
            base_tmp_dir.mkdir(exist_ok=True)
            temp_file_path = base_tmp_dir / file.filename
            file.save(temp_file_path)

            temp_dir, file_names = unzip_folder(temp_file_path)
            tmp_dir = temp_dir  # Update tmp_dir if a file is uploaded
        parameters = extract_parameters(
            str(question),
            function_definitions_llm=function_definitions_objects_llm[matched_function],
        )

        if parameters is None:
            parameters = []

        solution_function = functions_dict.get(
            matched_function, lambda *args, **kwargs: "No matching function found"
        )

        # Get how many arguments the function actually takes
        import inspect
        sig = inspect.signature(solution_function)
        num_params = len(sig.parameters)

        # Call based on function signature
        if num_params == 0:
            answer = solution_function()
        elif file and num_params >= 1:
            answer = solution_function(temp_dir, *parameters)
        else:
            answer = solution_function(*parameters)

        return jsonify({"answer": answer})
    except Exception as e:
        print(e,"this is the error")
        return jsonify({"error": str(e)}), 500


@app.route('/redeploy', methods=['GET'])
def redeploy():
    password = request.args.get('password')
    print(password)
    print(SECRET_PASSWORD)
    if password != SECRET_PASSWORD:
        return "Unauthorized", 403

    subprocess.run(["../redeploy.sh"], shell=True)
    return "Redeployment triggered!", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8000", debug=True)
