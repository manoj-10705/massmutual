try:
    from frontend.app import app
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
