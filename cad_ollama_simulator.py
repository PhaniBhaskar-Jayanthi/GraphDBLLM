# Disclaimer: Sample code. Not ready for production. Use as a reference for building your own CAD simulator with Ollama tool calling.
# This is a local CAD simulator that uses Ollama's tool calling to execute CAD operations based on user commands. 
# It simulates a simple CAD environment where you can create sketches, extrude them into bodies, and cut holes. 
# The state of the model is maintained in memory, and you can query it at any time.
import ollama
from typing import Dict, Any, List
import json

# ====================== SIMULATED CAD STATE ======================
class ModelState:
    def __init__(self):
        self.sketch_counter = 0
        self.body_counter = 0
        self.hole_counter = 0
        self.objects: Dict[str, Dict] = {}  # id -> info

state = ModelState()

# ====================== TOOL FUNCTIONS ======================

def create_rectangle_sketch(width: float, height: float, center: List[float] = [0, 0], plane: str = "xy") -> str:
    """Create a 2D rectangular sketch."""
    state.sketch_counter += 1
    sketch_id = f"sketch_{state.sketch_counter:03d}"
    state.objects[sketch_id] = {
        "type": "sketch",
        "shape": "rectangle",
        "width": width,
        "height": height,
        "center": center,
        "plane": plane
    }
    print("*"*60)
    print(f"✅ Created {sketch_id}: Rectangle {width}×{height} mm")
    return sketch_id


def extrude_profile(profile_id: str, distance: float, direction: str = "normal", operation: str = "new_body") -> Dict:
    """Extrude a 2D profile into a 3D body."""
    if profile_id not in state.objects:
        return {"error": f"Profile {profile_id} not found"}

    state.body_counter += 1
    body_id = f"body_{state.body_counter:03d}"
    top_face = f"{body_id}_top"
    bottom_face = f"{body_id}_bottom"

    state.objects[body_id] = {
        "type": "body",
        "from_profile": profile_id,
        "height": distance,
        "top_face": top_face,
        "bottom_face": bottom_face,
        "type": "Extrusion",
        "shape": "Cuboid",
    }

    print("*"*60)
    print(f"✅ Extruded {profile_id} → {body_id} (height: {distance}mm)")
    return {
        "body_id": body_id,
        "top_face": top_face,
        "bottom_face": bottom_face,
        "status": "success"
    }


def circular_cut_on_face(body_id: str, face_id: str, center: List[float], radius: float, depth: str = "through_all") -> str:
    """Cut a circular hole on a selected face."""
    if body_id not in state.objects:
        return f"Error: Body {body_id} not found"
    if not face_id.startswith(body_id):
        return f"Error: Face {face_id} does not belong to {body_id}"

    print("*"*60)
    print(f"✅ Circular cut on {body_id} / {face_id}")
    print(f"   Center: {center}, Radius: {radius}mm, Depth: {depth}")

    state.hole_counter += 1
    hole_id = f"hole_{state.hole_counter:03d}"
    
    state.objects[hole_id] = {
        "type": "hole",
        "shape": "cylinder",
        "center": center,
        "radius": radius,
        "depth": depth,
        "face": face_id,
        "body": body_id
    }

    return f"Success: Hole cut on {face_id}"


def get_model_state() -> str:
    """Return current model summary."""
    if not state.objects:
        return "Model is empty."
    print("*"*60)
    summary = "Current Model State:\n"
    for oid, obj in state.objects.items():
        summary += f"  - {oid}: {obj.get('type')} {obj.get('shape', '')} {obj.get('height', '')}\n"
    print("*"*60)
    return summary


# Map tool names to actual functions
available_functions = {
    "create_rectangle_sketch": create_rectangle_sketch,
    "extrude_profile": extrude_profile,
    "circular_cut_on_face": circular_cut_on_face,
    "get_model_state": get_model_state,
}

# ====================== MAIN AGENT LOOP ======================

def run_cad_agent():
    print("=== Local CAD Simulator with Ollama Tool Calling ===\n")
    print("Type your commands (e.g. 'Create a 100x60 rectangle sketch')")
    print("Type 'quit' or 'exit' to stop.\n")

    messages: List[Dict] = [
        {
            "role": "system",
            "content": (
                "You are a helpful CAD assistant for a solid modeling tool. "
                "Use the provided tools to perform operations. "
                "Always use previous results (IDs) for subsequent operations. "
                "Be precise with parameters. If unsure, ask for clarification."
                "Break down complex tasks into simpler steps and chain tool calls as needed."
            )
        }
    ]

    model_name = "gemma4:latest"   # Change to your preferred model

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        # Call Ollama with tools
        tools = [
            create_rectangle_sketch,
            extrude_profile,
            circular_cut_on_face,
            get_model_state
        ]
        try:
            response = ollama.chat(
                model=model_name,
                messages=messages,
                tools=tools
            )

            # Loop until the model stops requesting tool calls
            while response.message.tool_calls:
                # Append the assistant's message (with tool_calls) to history
                messages.append(response.message)

                for tool_call in response.message.tool_calls:
                    tool_name = tool_call.function.name
                    arguments = tool_call.function.arguments

                    print("*"*60)
                    print(f"\n🤖 Tool Selected: {tool_name}")
                    print(f"Parameters: {json.dumps(arguments, indent=2)}")

                    # Execute the tool
                    if tool_name in available_functions:
                        func = available_functions[tool_name]
                        try:
                            result = func(**arguments)
                            tool_result = str(result)
                        except Exception as e:
                            tool_result = f"Error executing {tool_name}: {str(e)}"
                    else:
                        tool_result = f"Unknown tool: {tool_name}"

                    print(f"Result: {tool_result}\n")

                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": tool_result
                    })

                # Call again with tools so the model can chain further calls
                response = ollama.chat(model=model_name, messages=messages, tools=tools)

            # No (more) tool calls — print the final text response
            if response.message.content:
                messages.append(response.message)
                print(f"Assistant: {response.message.content}\n")
            else:
                # No tool called and no content — just normal response
                print(f"Assistant: {response.message.content}\n")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_cad_agent()

# Create a rectangle sketch 100mm by 60mm centered at origin
# Extrude the 2D profile by 50mm
# Cut a circular hole of 15mm radius on the top of the extruded object
# Show current model state

# This code works even when the entire steps are concatenated into one step
# Create a rectangle sketch 100mm by 60mm centered at origin, extrude the 2D profile by 50mm, then cut a circular hole of 15mm radius on the top of the extruded object and finally show current model state.