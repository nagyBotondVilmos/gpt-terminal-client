import shutil
import os

# In-memory store for pending copy plans
COPY_PLANS = {}

def copy_files_plan(source: str, destination: str, plan_id: str = None):
    """
    Step 1: generate a plan for copying files.
    Returns a human-readable summary and the command it would execute.
    """
    if not os.path.exists(source):
        return f"Source path does not exist: {source}"

    if not plan_id:
        plan_id = f"plan_{len(COPY_PLANS) + 1}"

    # Create plan (just a summary + command string)
    command = f"shutil.copytree('{source}', '{destination}')" if os.path.isdir(source) else f"shutil.copy('{source}', '{destination}')"
    summary = f"Plan ID: {plan_id}\nCopy from: {source}\nCopy to: {destination}\nCommand: {command}"

    COPY_PLANS[plan_id] = {
        "source": source,
        "destination": destination,
        "command": command,
        "approved": False
    }

    return summary

def copy_files_execute(plan_id: str, approve: bool = True):
    """
    Step 2: execute the approved plan.
    """
    plan = COPY_PLANS.get(plan_id)
    if not plan:
        return f"No plan found with ID: {plan_id}"

    if not approve:
        return f"Plan {plan_id} rejected by user. No action taken."

    try:
        src = plan["source"]
        dst = plan["destination"]

        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy(src, dst)

        plan["approved"] = True
        return f"Plan {plan_id} executed successfully. {src} copied to {dst}"
    except Exception as e:
        return f"Error executing plan {plan_id}: {e}"
