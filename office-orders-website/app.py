from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime

from rag_service import OfficeOrdersRAG

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")
TIMETABLE_FILE = os.path.join(BASE_DIR, "timetable.json")
rag_service = OfficeOrdersRAG()


def load_orders():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_orders(orders):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=4, ensure_ascii=False)


def load_timetable():
    if not os.path.exists(TIMETABLE_FILE):
        return []
    with open(TIMETABLE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_timetable(data):
    with open(TIMETABLE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def generate_id():
    return int(datetime.now().timestamp())



# Homepage
@app.route("/")
def home():
    return render_template("home.html")


# Office Orders Page
@app.route("/office-orders")
def office_orders():
    orders = load_orders()

    # Sort latest first
    orders.sort(key=lambda x: x.get("release_date", ""), reverse=True)

    return render_template("index.html", orders=orders)


# Timetable Page
@app.route("/timetable")
def timetable():
    data = load_timetable()
    return render_template("timetable.html", timetable=data)


@app.route("/office-orders/chat")
def office_orders_chat():
    return render_template("chat.html")


# CREATE
@app.route("/api/office-orders", methods=["POST"])
def create_office_order():
    data = request.json
    orders = load_orders()

    new_order = {
        "id": generate_id(),
        "subject": data.get("subject", ""),
        "category": data.get("category", ""),
        "subcategory": data.get("subcategory", ""),
        "content": data.get("content", ""),
        "release_date": data.get("release_date", ""),
        "effective_from": data.get("effective_from", ""),
        "effective_to": data.get("effective_to", ""),
        "pdf_path": data.get("pdf_path", "")
    }

    orders.append(new_order)
    save_orders(orders)

    return jsonify({
        "status": "success",
        "message": "Office order created",
        "id": new_order["id"]
    }), 201


# GET (VERY IMPORTANT for your frontend auto-refresh)
@app.route("/api/office-orders", methods=["GET"])
def get_office_orders():
    orders = load_orders()

    # Sort latest first
    orders.sort(key=lambda x: x.get("release_date", ""), reverse=True)

    return jsonify(orders)


# UPDATE
@app.route("/api/office-orders/<int:order_id>", methods=["PUT"])
def update_office_order(order_id):
    data = request.json
    orders = load_orders()

    for order in orders:
        if order["id"] == order_id:
            order.update({
                "subject": data.get("subject", order["subject"]),
                "category": data.get("category", order.get("category", "")),
                "subcategory": data.get("subcategory", order.get("subcategory", "")),
                "content": data.get("content", order["content"]),
                "release_date": data.get("release_date", order["release_date"]),
                "effective_from": data.get("effective_from", order.get("effective_from", "")),
                "effective_to": data.get("effective_to", order.get("effective_to", "")),
                "pdf_path": data.get("pdf_path", order["pdf_path"])
            })
            save_orders(orders)
            return jsonify({"status": "success", "message": "Office order updated"})

    return jsonify({"status": "error", "message": "Order not found"}), 404


# DELETE
@app.route("/api/office-orders/<int:order_id>", methods=["DELETE"])
def delete_office_order(order_id):
    orders = load_orders()
    updated_orders = [o for o in orders if int(o["id"]) != int(order_id)]

    if len(updated_orders) == len(orders):
        return jsonify({"status": "error", "message": "Order not found"}), 404

    save_orders(updated_orders)
    return jsonify({"status": "success", "message": "Office order deleted"})


@app.route("/api/timetable", methods=["POST"])
def add_timetable():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON received"}), 400

        timetable = load_timetable()

        new_entry = {
            "id": generate_id(),
            "subject": data.get("subject", "Timetable"),
            "date": data.get("date", ""),
            "file": data.get("file", "")
        }

        timetable.append(new_entry)
        save_timetable(timetable)

        return jsonify({"status": "success"}), 201

    except Exception as e:
        print("🔥 ERROR in /api/timetable:", str(e))
        return jsonify({"error": str(e)}), 500

# GET timetable (for UI)
@app.route("/api/timetable", methods=["GET"])
def get_timetable():
    return jsonify(load_timetable())

@app.route("/api/timetable/<int:item_id>", methods=["DELETE"])
def delete_timetable(item_id):
    timetable = load_timetable()

    updated = [t for t in timetable if t["id"] != item_id]

    if len(updated) == len(timetable):
        return jsonify({"status": "error", "message": "Not found"}), 404

    save_timetable(updated)

    return jsonify({"status": "success"})


@app.route("/api/rag/status", methods=["GET"])
def rag_status():
    try:
        status = rag_service.ensure_index()
        return jsonify(status)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/rag/rebuild", methods=["POST"])
def rag_rebuild():
    try:
        status = rag_service.ensure_index(force_rebuild=True)
        return jsonify(status)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/rag/ask", methods=["POST"])
def rag_ask():
    try:
        data = request.get_json() or {}
        question = (data.get("question") or "").strip()
        top_k = int(data.get("top_k", 5))

        if not question:
            return jsonify({"status": "error", "message": "Question is required"}), 400

        result = rag_service.answer_query(question, top_k=top_k)
        result["status"] = "success"
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def start_flask():
    app.run(port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    app.run(debug=True)
