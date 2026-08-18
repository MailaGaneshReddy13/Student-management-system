import os
import json
import urllib.request
import urllib.error

def get_api_key():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = "AQ.Ab8RN6IsHWuTCmfneZJ3_VXHJ8jaUSXeKAHqZtFXXkmHc3V_Eg"
    return api_key

def ask_gemini(prompt, system_instruction=None):
    api_key = get_api_key()
    if not api_key:
        return "Gemini API key is missing. Please configure it in your settings."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    data = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }
    
    if system_instruction:
        data["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
        
    req_body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=req_body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            return res_json['candidates'][0]['content']['parts'][0]['text']
    except urllib.error.HTTPError as e:
        status_code = e.code
        err_text = e.read().decode('utf-8')
        if status_code in (400, 403):
            return f"API Key Error ({status_code}): Please make sure your Gemini API key is valid."
        return f"Gemini API Error {status_code}: {err_text}"
    except Exception as e:
        return f"Could not connect to Gemini API: {str(e)}"

def generate_performance_recommendations(student_name, department, year, subjects, attendance_rate):
    """Generates personalized study recommendation checklist for a student."""
    subjects_str = ", ".join([f"{s['subject_name']}: {s['marks_obtained']}/{s['max_marks']} ({s['grade']})" for s in subjects])
    
    prompt = f"""
    Analyze the performance of student {student_name} ({department}, {year}).
    Subject Marks: {subjects_str if subjects_str else 'No subjects registered yet.'}
    Attendance Rate: {attendance_rate}%

    Provide structured, actionable advice:
    1. Overall performance review.
    2. Focus areas (specifically call out subjects with grade C, D, E or F).
    3. Actionable study strategies or resources.
    4. Attendance recommendation.
    Keep the tone encouraging, structured and concise.
    """
    
    system_instruction = "You are an expert academic counselor at a university. Provide professional, structured study advice."
    return ask_gemini(prompt, system_instruction)
