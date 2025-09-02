import os
import json
from flask import Flask, request, jsonify, send_from_directory, render_template
from openai import OpenAI
from dotenv import load_dotenv
from flask_cors import CORS
import re

# --- Load environment variables ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OpenAI API key not found! Add it to your .env file.")

client = OpenAI(api_key=OPENAI_API_KEY)

MODEL = "gpt-3.5-turbo"


# --- Flask setup ---
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# --- In-memory task store ---
tasks = []
task_counter = 1

def addTask(title, description=""):
    global task_counter
    task = {"id": task_counter, "title": title, "description": description, "completed": False}
    tasks.append(task)
    task_counter += 1
    return task

def getTasks():
    return tasks

def completeTask(task_id):
    for task in tasks:
        if task["id"] == task_id:
            task["completed"] = True
            return task
    return {"error": "Task not found"}

def deleteTask(task_id):
    global tasks
    tasks = [t for t in tasks if t["id"] != task_id]
    return {"status": "deleted"}

def toggleComplete(task_id, completed):
    for task in tasks:
        if task["id"] == task_id:
            task["completed"] = completed
            return task
    return None

# --- OpenAI function definitions ---
tools = [
    {
        "name": "addTask",
        "description": "Add a new task to the to-do list.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "getTasks",
        "description": "Retrieve all tasks.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "completeTask",
        "description": "Mark a task as completed by ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "deleteTask",
        "description": "Delete a task by ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "toggleComplete",
        "description": "Toggle task complete/pending status by ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "Task ID"},
                "completed": {"type": "boolean", "description": "True if complete, False if pending"}
            },
            "required": ["task_id", "completed"]
        }
    }
]

# --- Serve frontend ---
@app.route("/")
def index():
    return render_template("index.html")

# --- REST API endpoints ---
@app.route("/api/v1/todos", methods=["POST"])
def api_add_task():
    data = request.json
    task = addTask(data["title"], data.get("description", ""))
    return jsonify(task), 201

@app.route("/api/v1/todos", methods=["GET"])
def api_get_tasks():
    return jsonify(getTasks()), 200

@app.route("/api/v1/todos/<int:task_id>", methods=["PATCH"])
def api_toggle_complete_task(task_id):
    data = request.json
    if "completed" in data:
        for task in tasks:
            if task["id"] == task_id:
                task["completed"] = bool(data["completed"])  # true or false
                return jsonify(task), 200
        return jsonify({"error": "Task not found"}), 404
    return jsonify({"error": "Invalid request"}), 400

@app.route("/api/v1/todos/<int:task_id>", methods=["DELETE"])
def api_delete_task(task_id):
    return jsonify(deleteTask(task_id)), 200

# --- Chatbot endpoint ---
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")

    SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are an AI Task Manager assistant. "
        "You can help users manage tasks by adding, listing, completing, or deleting them. "
        "Always confirm actions and use a friendly, concise tone."
        )
    }


    response = client.chat.completions.create(
        model=MODEL,
        messages=[SYSTEM_PROMPT,{"role": "user", "content": user_message}],
        functions=tools,
        function_call="auto"
    )


    message = response.choices[0].message  # ChatCompletionMessage object

    # If AI wants to call a function
    if hasattr(message, "function_call") and message.function_call:
        func_call = message.function_call
        func_name = func_call.name
        func_args = json.loads(func_call.arguments or "{}")

        # Call the Python function
        if func_name == "addTask":
            result = addTask(**func_args)
        elif func_name == "getTasks":
            result = getTasks()
        elif func_name == "completeTask":
            result = completeTask(**func_args)
        elif func_name == "deleteTask":
            result = deleteTask(**func_args)
        elif func_name == "toggleComplete":
            result = toggleComplete(**func_args)
        else:
            result = {"error": "Unknown function"}

        # --- Pretty format ---
        if isinstance(result, list):
            pretty = "\n".join(
                [f"{t['id']}. {t['title']} - {'✅ Completed' if t['completed'] else '❌ Pending'}"
                 for t in result]
            )
        elif isinstance(result, dict):
            if "id" in result:
                pretty = f"Task {result['id']}: {result['title']} - {'✅ Completed' if result.get('completed') else '❌ Pending'}"
            elif result.get("status") == "deleted":
                pretty = "Task deleted successfully."
            else:
                pretty = json.dumps(result)
        else:
            pretty = str(result)

        return jsonify({"reply": pretty})

    # Otherwise just return AI's text
    return jsonify({"reply": message.content})


if __name__ == "__main__":
    # os.makedirs("static", exist_ok=True)
    # print("Serving on http://127.0.0.1:5000")
    app.run(debug=True)
