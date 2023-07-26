def version_utils():
    """gives the version of utils.py"""
    return "1.2.0"

def version_data():
    """gives the version of gather_data.py"""
    return "1.1.1"

def version_model():
    """gives the version of model.py"""
    return "1.2.0"

def version_remove():
    """gives the version of remove_fringing.py"""
    return "1.0.0"

def version_all():
    """gives the version of the entire script"""
    return "1.3.0"

if __name__ == "__main__":
    print("script version : {}\n".format(version_all()))
    print("utils.py version : {}".format(version_utils()))
    print("gather_data.py version : {}".format(version_data()))
    print("model.py version : {}".format(version_model()))
    print("remove_fringing.py version : {}".format(version_remove()))