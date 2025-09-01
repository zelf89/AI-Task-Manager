const API_URL = "/api/v1/todos";
const CHAT_URL = "/chat";

// --- Load tasks ---
async function loadTasks() {
  const res = await fetch(API_URL);
  const tasks = await res.json();

  const pendingList = document.getElementById("pendingTasks");
  const completedList = document.getElementById("completedTasks");

  pendingList.innerHTML = "";
  completedList.innerHTML = "";

  tasks.forEach((task) => {
    const li = document.createElement("li");
    li.textContent = `Task ${task.id}: ${task.title} - ${
      task.completed ? "✅ Completed" : "⏳ Pending"
    }`;

    // Toggle complete / undo button
    const btnToggle = document.createElement("button");
    btnToggle.textContent = task.completed ? "↩ Undo" : "✓ Complete";
    btnToggle.onclick = () => toggleComplete(task.id, !task.completed);

    // Delete button
    const btnDelete = document.createElement("button");
    btnDelete.textContent = "🗑 Delete";
    btnDelete.onclick = () => deleteTask(task.id);

    li.appendChild(btnToggle);
    li.appendChild(btnDelete);

    if (task.completed) {
      completedList.appendChild(li);
    } else {
      pendingList.appendChild(li);
    }
  });
}

// --- Toggle complete / undo ---
async function toggleComplete(id, completed) {
  await fetch(`${API_URL}/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ completed }),
  });
  loadTasks();
}

// --- Add task ---
async function addTask() {
  const title = document.getElementById("taskTitle").value;
  if (!title) return;
  await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  document.getElementById("taskTitle").value = "";
  loadTasks();
}

// --- Delete task ---
async function deleteTask(id) {
  await fetch(`${API_URL}/${id}`, { method: "DELETE" });
  loadTasks();
}

// --- Chatbot ---
async function sendChat() {
  const input = document.getElementById("chatInput");
  const msg = input.value;
  if (!msg) return;

  const chatBox = document.getElementById("chatMessages");

  // Display user message
  const userMsg = document.createElement("div");
  userMsg.className = "chat-message user";
  userMsg.textContent = msg;
  chatBox.appendChild(userMsg);

  // Send to backend
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: msg }),
  });
  const data = await res.json();

  // Display AI reply
  const botMsg = document.createElement("div");
  botMsg.className = "chat-message bot";
  botMsg.textContent = data.reply;
  chatBox.appendChild(botMsg);

  chatBox.scrollTop = chatBox.scrollHeight;
  input.value = "";

  // Reload tasks list
  loadTasks();
}

// --- Initial load ---
loadTasks();
