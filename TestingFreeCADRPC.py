# Just for testing the FreeCAD RPC server, to confirm it can create a document, 
# add an object, and return a screenshot. 
# For Demo only and not intended for production use, so no error handling or cleanup is done.
# Assumes that the FreeCAD RPC server is running and listening on port 9875
import xmlrpc.client

proxy = xmlrpc.client.ServerProxy("http://localhost:9875", allow_none=True)

# Step 1 — delete TestDoc if it already exists, then recreate it
existing_docs = proxy.list_documents()
if "TestDoc" in existing_docs:
    proxy.execute_code("import FreeCAD; FreeCAD.closeDocument('TestDoc')")
proxy.create_document("TestDoc")

# Step 2 — create a box
obj_data = {
    "Name": "MyBox",
    "Type": "Part::Box",
    "Properties": {"Length": 50, "Width": 50, "Height": 25},
}
proxy.create_object("TestDoc", obj_data)

# Step 3 — take a screenshot to confirm visually
screenshot = proxy.get_active_screenshot("Isometric")   # returns base64-encoded PNG
import base64, pathlib
pathlib.Path("view.png").write_bytes(base64.b64decode(screenshot))
print("Screenshot saved to view.png")