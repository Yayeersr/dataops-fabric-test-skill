# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

def greet(name):
    """Return a greeting; empty or blank name falls back to 'world'."""
    name = (name or "").strip()
    return f"Hello, {name or 'world'}!"


print(greet("CI/CD"))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
