from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from collections import OrderedDict
from functools import wraps
from dotenv import load_dotenv
import os, httpx, json, csv, io, re
from datetime import datetime
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "tsl-dev-secret-2025")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

GALLERY_FOLDER    = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'images', 'gallery')
GALLERY_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gallery_data.json')
APPS_EXTRA_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apps_extra.json')
PUBS_EXTRA_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pubs_extra.json')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'avif', 'webp'}

def allowed_file(f): return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def load_events():
    if not os.path.exists(GALLERY_DATA_FILE): return []
    with open(GALLERY_DATA_FILE,'r',encoding='utf-8') as f: return json.load(f)

def save_events(events):
    with open(GALLERY_DATA_FILE,'w',encoding='utf-8') as f: json.dump(events,f,ensure_ascii=False,indent=2)

def event_photos(key):
    folder = os.path.join(GALLERY_FOLDER, key)
    if not os.path.exists(folder): return []
    photos = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder,f)) and allowed_file(f)]
    photos.sort(key=lambda f: os.path.getmtime(os.path.join(folder,f)))
    return photos

def load_extra_apps():
    if not os.path.exists(APPS_EXTRA_FILE): return []
    with open(APPS_EXTRA_FILE,'r',encoding='utf-8') as f: return json.load(f)

def save_extra_apps(data):
    with open(APPS_EXTRA_FILE,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)

def load_extra_pubs():
    if not os.path.exists(PUBS_EXTRA_FILE): return []
    with open(PUBS_EXTRA_FILE,'r',encoding='utf-8') as f: return json.load(f)

def save_extra_pubs(data):
    with open(PUBS_EXTRA_FILE,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)

def sb(method, path, data=None, params=""):
    if not SUPABASE_URL or not SUPABASE_KEY: return []
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json", "Prefer": "return=representation"}
    url = f"{SUPABASE_URL}/rest/v1/{path}{params}"
    try:
        with httpx.Client(timeout=10) as c:
            if method=="GET":     r=c.get(url,headers=headers)
            elif method=="POST":  r=c.post(url,headers=headers,json=data)
            elif method=="PATCH": r=c.patch(url,headers=headers,json=data)
            elif method=="DELETE":r=c.delete(url,headers=headers)
            else: return []
        return r.json() if r.text else []
    except Exception as e:
        print(f"Supabase error: {e}"); return []

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "researcher" not in session: return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ─── Site-wide ───────────────────────────────────────────────
PROFESSOR = {
    "name":      "Yun-Jung Choi",
    "title":     "Professor",
    "bio":       "Professor Yun-Jung Choi is a nurse educator and researcher at the Red Cross College of Nursing, Chung-Ang University, Seoul, Korea.",
    "email":     "yunjungchoi@cau.ac.kr",
    "office":    "+82-2-820-6907",
    "lab_phone": "+82-2-820-5986",
    "address":   "Red Cross College of Nursing, Chung-Ang University, Seoul, South Korea",
    "photo":     "images/professor-placeholder.jpg",
}

RESEARCH_TOPICS = [
    {"key": "brainwave",   "title": "Brain Wave",              "summary": "Focused on Alpha waves to stabilise the mind, relieve stress, and improve learning efficiency.",         "image": "images/brain_wave.avif",  "gradient": "linear-gradient(135deg,#004d40 0%,#26a69a 100%)"},
    {"key": "simulation",  "title": "Simulation Education",    "summary": "Developing simulations using standardised patients and interactive PFA serious games.",                   "image": "images/simulation.avif",  "gradient": "linear-gradient(135deg,#1a237e 0%,#5c6bc0 100%)"},
    {"key": "binaural",    "title": "Binaural Beat",           "summary": "Developing binaural beats and modulating brainwaves to promote mental wellbeing.",                       "image": "images/binaural.avif",    "gradient": "linear-gradient(135deg,#4a148c 0%,#ab47bc 100%)"},
    {"key": "app",         "title": "Developing Applications", "summary": "Building evidence-based mobile apps for disaster survivors and healthcare workers.",                     "image": "images/app.avif",         "gradient": "linear-gradient(135deg,#0F6B6B 0%,#1ec0c0 100%)"},
]

TEAM = {
    "phd": [
        {"name": "Hae-In Namgung",  "interest": "Simulation education, intervention research, RCT, PTSD, Artificial intelligence (AI)", "image": "images/member-haein-placeholder.jpg"},
        {"name": "Jae-Won Kwak",    "interest": "Community mental health nursing, community addiction management",                        "image": "images/member-jaewon-placeholder.jpg"},
        {"name": "Joo-Young Jin",   "interest": "Nursing simulation, disaster nursing, psychological safety",                            "image": "images/member-jooyoung-placeholder.jpg"},
    ],
    "ma": [
        {"name": "Chae-Young Lee",  "interest": "Anxiety, PTSD, depression, suicide, addiction",                                       "image": "images/member-chaeyoung-placeholder.jpg"},
    ],
    "alumni": [
        {"name": "Run-Ju Choi",   "image": "images/run-ju_choi.avif",    "current_position": ""},
        {"name": "Eun-Jung Ko",   "image": "images/eunjung_ko.avif",     "current_position": ""},
        {"name": "Younjoo Um",    "image": "images/younjoo_um.avif",     "current_position": ""},
        {"name": "Dong-Hee Cho",  "image": "images/dong-hee_cho.avif",   "current_position": ""},
        {"name": "Hee-Won Song",  "image": "images/hee-won_song.avif",   "current_position": ""},
    ],
}

APPS = [
    {
        "key":       "pls",
        "icon":      "🫀",
        "gradient":  "linear-gradient(135deg,#00695c 0%,#26a69a 100%)",
        "name":      "PLS",
        "full_name": "Psychological Life Support",
        "label":     "Mobile PFA Application",
        "desc_kr":   "재난구호자를 위한 심리적인명구조술 PLS는\n재난상황에 대한 정보제공 및 심리적응급처치 기술 적용,\n재난 후 구호요원들의 마음회복을 돕기위한 앱입니다.",
        "desc_en":   "PLS (Psychological Life Skill) for disaster relief workers is providing information on disaster situations and application of psychological first aid techniques. It is a mobile app to help rescue workers recover their minds after a disaster.",
        "tags":      ["Disaster Workers", "Mental Health", "Psychological First Aid"],
        "screenshot": None,
        "content_img_kr": "images/pls_kr_content.avif",
        "content_img_en": "images/pls_en_content.avif",
        "dl_kr":  "https://m.onestore.co.kr/ko-kr/apps/appsDetail.omp?prodId=0000747597",
        "dl_en":  "https://m.onestore.co.kr/ko-kr/apps/appsDetail.omp?prodId=0000747600",
        "subsections": [],
    },
    {
        "key":       "tls",
        "icon":      "🌿",
        "gradient":  "linear-gradient(135deg,#1b5e20 0%,#66bb6a 100%)",
        "name":      "TLS",
        "full_name": "Training of Life Skills",
        "label":     "Mobile PFA Application",
        "desc_kr":   "재난경험자를 위한 마음치유기술 TLS (Training for Life Skills)는\n재난피해로 심리적 상처를 입은 분들의 심리회복을 돕기 위한 앱입니다.",
        "desc_en":   "TLS (Training for Life Skills) for disaster experienced people is an app to help the psychological recovery of those who have been psychologically wounded by disaster damage.",
        "tags":      ["Disaster Survivors", "Trauma Recovery", "Skills Training"],
        "screenshot": None,
        "content_img_kr": "images/tls_kr_content.avif",
        "content_img_en": "images/tls_en_content.avif",
        "dl_kr":  "https://m.onestore.co.kr/ko-kr/apps/appsDetail.omp?prodId=0000747598",
        "dl_en":  "https://m.onestore.co.kr/ko-kr/apps/appsDetail.omp?prodId=0000747605",
        "subsections": [],
    },
    {
        "key":       "mind_therapy",
        "icon":      "🧠",
        "gradient":  "linear-gradient(135deg,#311b92 0%,#9c27b0 100%)",
        "name":      "Mind Therapy",
        "full_name": "Neurofeedback Stress Management",
        "label":     "",
        "desc_kr":   "",
        "desc_en":   "The 'Mind Therapy' application is designed to help people recover from traumatic events. Developed by applying EEG and heart rate variability technology, it can measure left-right brain balance, brain activity, and stress recovery through real-time EEG/heart rate variability tests.",
        "tags":      ["Neurofeedback", "Binaural Beat", "Stress & PTSD"],
        "screenshot": "images/app_screenshot3.png",
        "content_img_kr": None,
        "content_img_en": None,
        "dl_kr":  None,
        "dl_en":  None,
        "subsections": [
            {
                "title": "Brain Therapy",
                "image": "images/mt_brain_therapy.avif",
                "desc":  "We offer a meditation program with neurofeedback and binaural beats.",
                "links": [
                    {"text": "Neurofeedback",  "url": None},
                    {"text": "Binaural beats", "url": None},
                ],
            },
            {
                "title": "Autonomic Nerve Therapy",
                "image": "images/mt_autonomic.avif",
                "desc":  "The deep breathing and butterfly hug programs are prepared for your autonomic nervous system stabilization. Several options for deep breathing are provided — choose whatever you feel comfortable with. A video guide for the butterfly hug is also included.",
                "links": [],
            },
            {
                "title": "Brain Game",
                "image": "images/mt_brain_game.avif",
                "desc":  "We visually represent the response when alpha waves are enhanced to help train the brain waves. The balloon's face will change along with your alpha waves. Enhance alpha waves through an exciting game!",
                "links": [],
            },
        ],
    },
]

# ─── Publications ────────────────────────────────────────────
ARTICLES = [
    # 2024
    {"year": 2024, "title": "Feasibility of a Mobile App for Traumatic Stress Management Using Neurofeedback-based Mediation and Binaural Beat Music: A Pilot Randomized Controlled Trial", "authors": "Choi, Y. J., Cho, D. H. & Lee, N. R.", "journal": "Digital Health, 10", "doi": "https://doi.org/10.1177/20552076241308986"},
    {"year": 2024, "title": "Mental Health Status and Related Factors of Citizens 6 Months after Mass Death and Injury Due to Crowd Crush Incident: Focused on the Itaewon Disaster in 2022", "authors": "Choi, Y. J., Song, H., Namgung, H. I. & Lee, N. R.", "journal": "Disaster Medicine and Public Health Preparedness, 19, e11", "doi": "https://doi.org/10.1017/dmp.2024.342"},
    {"year": 2024, "title": "Mediating effect of bicultural acceptability among multicultural adolescents in the relationship between depression and life satisfaction", "authors": "Choi, Y. J. & Um, Y. J.", "journal": "Archives of Psychiatric Nursing, 53", "doi": "https://doi.org/10.1016/j.apnu.2024.10.003"},
    {"year": 2024, "title": "Still in there—citizens' well-being and PTSD after Seoul Halloween crowd crush in Korea: A cross-sectional study", "authors": "Choi, Y. J. & Namgung, H. I.", "journal": "Scientific Reports, 14, 20537", "doi": "https://doi.org/10.1038/s41598-024-71631-9"},
    {"year": 2024, "title": "Development and Effect of an Interactive Simulated Education Program for Psychological First Aid: A Randomized Controlled Trial", "authors": "Choi, E. J. & Choi, Y. J.", "journal": "Journal of Nursing Management, 8806047", "doi": "https://doi.org/10.1155/2024/8806047"},
    {"year": 2024, "title": "Experiences of Family Caregiver of Older People with Dementia in Korea during the COVID-19 Pandemic: A Qualitative Analysis", "authors": "Joh, E. S. & Choi, Y. J.", "journal": "Journal of Gerontological Nursing, 50(10)", "doi": "https://doi.org/10.3928/00989134-20240916-01"},
    {"year": 2024, "title": "The Association between Fear of COVID-19, Obsession with COVID-19, and Post Traumatic Stress Disorder in Korean Emergency Rescue Firefighters", "authors": "Choi, Y. J. & Song, H.", "journal": "International Journal of Mental Health Promotion, 26(6)", "doi": "https://doi.org/10.32604/ijmhp.2024.050824"},
    {"year": 2024, "title": "Citizens' Mental Health Issues and Psychological Trauma Experience due to a Crowd-Crush Disaster in Korea", "authors": "Choi, Y. J., Kwak, J. W. & Namgung, H. I.", "journal": "International Journal of Mental Health Promotion, 26(6)", "doi": "https://doi.org/10.32604/ijmhp.2024.050458"},
    {"year": 2024, "title": "Efficacy of a virtual nursing simulation-based education to provide psychological support for patients affected by infectious disease disasters: a randomized controlled trial", "authors": "Ko, E. & Choi, Y. J.", "journal": "BMC Nursing, 23, 230", "doi": "https://doi.org/10.1186/s12912-024-01901-4"},
    {"year": 2024, "title": "Effectiveness of a fire disaster PFA simulation game: A single-blinded trial", "authors": "Choi, Y. J. & Song, H.", "journal": "Disaster Medicine and Public Health Preparedness, 18, e64", "doi": "https://doi.org/10.1017/dmp.2024.47"},
    {"year": 2024, "title": "The Development, Implementation, and Evaluation of a Geriatric Disaster Nursing Simulation Intervention With Supportive Debriefing", "authors": "Jin, J. Y. & Choi, Y. J.", "journal": "Simulation in Healthcare, 19(5)", "doi": "https://doi.org/10.1097/SIH.0000000000000780"},
    # 2023
    {"year": 2023, "title": "What Influenced Frontline Nurses' Mental Health During the Early Phase of the Covid-19 Pandemic", "authors": "Choi, Y. J., Um, Y. J. & Cho, D. H.", "journal": "International Nursing Review, 70(4)", "doi": "https://doi.org/10.1111/inr.12895"},
    {"year": 2023, "title": "Development of a Multiple-Patient Simulation and its Effectiveness in Clinical Judgment and Practice Readiness: A Randomized Controlled Trial", "authors": "Namgung, H. I., Choi, Y. J. & Kang, J. S.", "journal": "Clinical Simulation in Nursing, 83, 101448", "doi": "https://doi.org/10.1016/j.ecns.2023.101448"},
    {"year": 2023, "title": "Effects of a web-based education for community mental health case managers on physical healthcare for clients with severe mental illness", "authors": "Lee, J. & Choi, Y. J.", "journal": "AIMS Public Health, 10(3)", "doi": "https://doi.org/10.3934/publichealth.2023045"},
    {"year": 2023, "title": "Neurofeedback Effect on Symptoms of Posttraumatic Stress Disorder: A Systematic Review and Meta-Analysis", "authors": "Choi, Y. J., Choi, E. J. & Ko, E.", "journal": "Applied Psychophysiology and Biofeedback, 48", "doi": "https://doi.org/10.1007/s10484-023-09593-3"},
    {"year": 2023, "title": "Inpatient meditation for alcohol use disorder reduces mood dysregulation: A pilot study", "authors": "Choi, Y. J., Cho, D. H. & Lee, N. R.", "journal": "Social Behavior and Personality, 51(10)", "doi": "https://doi.org/10.2224/sbp.12451"},
    {"year": 2023, "title": "Professional quality of life, resilience, posttraumatic stress and leisure activity among intensive care unit nurses", "authors": "Shin, N. & Choi, Y. J.", "journal": "International Nursing Review", "doi": "https://doi.org/10.1111/inr.12850"},
    {"year": 2023, "title": "Effects of a mental health nursing simulation for general ward nurses: A pilot study", "authors": "Lee, M. Y. & Choi, Y. J.", "journal": "Nursing Open, 10(5)", "doi": None},
    {"year": 2023, "title": "Topic Models to Analyze Disaster-Related Newspaper Articles: Focusing on COVID-19", "authors": "Choi, Y. J. & Um, Y. J.", "journal": "International Journal of Mental Health Promotion, 25(3)", "doi": None},
    {"year": 2023, "title": "Disaster Healthcare Workers' Experience of Using the Psychological First Aid Mobile App During Disaster Simulation Training", "authors": "Choi, Y. J., Jung, H. S., Choi, E. J. & Ko, E.", "journal": "Disaster Medicine and Public Health Preparedness, 17, e55", "doi": None},
    {"year": 2023, "title": "The early emotional responses and central issues of people in the epicenter of the COVID-19 pandemic: An analysis from twitter text mining", "authors": "Choi, E. J. & Choi, Y. J.", "journal": "International Journal of Mental Health Promotion", "doi": None},
    # 2022
    {"year": 2022, "title": "Student nurse experiences in public healthcare clinical practice during the COVID-19 pandemic: A qualitative study", "authors": "Choi, Y. J. & Um, Y. J.", "journal": "Nurse Education Today, 119, 105586", "doi": None},
    {"year": 2022, "title": "The effects of a home-visit nursing simulation for older people with dementia on nursing students' communication skills, self-efficacy, and critical thinking propensity", "authors": "Choi, Y. J. & Um, Y. J.", "journal": "Nurse Education Today, 119, 105564", "doi": None},
    {"year": 2022, "title": "Standardized patient experiences study on clinical performance evaluation of nursing college students' ability: A qualitative study", "authors": "Choi, Y. J., Won, M. R. & Yoo, S. Y.", "journal": "Nurse Education Today, 118, 105437", "doi": None},
    {"year": 2022, "title": "Effects of Nursing Care Using Binaural Beat Music on Anxiety, Pain, and Vital Signs in Surgery Patients", "authors": "Jang, Y. & Choi, Y. J.", "journal": "Journal of PeriAnesthesia Nursing, 37(6)", "doi": None},
    {"year": 2022, "title": "A grounded theory on school nursing experiences with major pandemic diseases", "authors": "Um, Y. J. & Choi, Y. J.", "journal": "INQUIRY: The Journal of Health Care Organization, 59", "doi": None},
    {"year": 2022, "title": "A simulation-based nursing education of psychological first aid for adolescents exposed to hazardous chemical disasters", "authors": "Kim, H. W. & Choi, Y. J.", "journal": "BMC Medical Education, 22(1)", "doi": None},
    {"year": 2022, "title": "Simulation-based education for nurses in caring for the psychological well-being of survivors of disaster", "authors": "Yun, S. M. & Choi, Y. J.", "journal": "The Journal of Continuing Education in Nursing, 53(3)", "doi": None},
    {"year": 2022, "title": "Clinical Nurses' Continuing Education Needs in Acute Burn Care", "authors": "Oh, D. & Choi, Y. J.", "journal": "The Journal of Continuing Education in Nursing, 53(2)", "doi": None},
    {"year": 2022, "title": "Efficacy of a Community-Based Trauma Recovery Program after a Fire Disaster", "authors": "Choi, Y. J., Won, M. R. & Cho, D. H.", "journal": "International Journal of Mental Health Promotion, 24", "doi": None},
    {"year": 2022, "title": "The effect of a simulated fire disaster psychological first aid training program on the self-efficacy, competence, and knowledge of mental health practitioners", "authors": "Park, J. S. & Choi, Y. J.", "journal": "Disaster Medicine and Public Health Preparedness, 16(1)", "doi": None},
    # 2021
    {"year": 2021, "title": "COVID-19 and risk factors of anxiety and depression in South Korea", "authors": "Hyun, J. et al.", "journal": "Psychiatry Investigation, 18(9)", "doi": None},
    {"year": 2021, "title": "Explicit and implicit attitudes toward people with COVID-19: Need for community mental health services", "authors": "Choi, Y. J. & Cho, D. H.", "journal": "Social Behavior and Personality, 49(11)", "doi": None},
    {"year": 2021, "title": "Managing traumatic stress using a mental health care mobile app: A pilot study", "authors": "Choi, Y. J., Ko, E. J., Choi, E. J. & Um, Y. J.", "journal": "International Journal of Mental Health Promotion, 23", "doi": None},
    {"year": 2021, "title": "The mediating effect of life satisfaction and the moderated mediating effect of social support on the relationship between depression and suicidal behavior among older adults", "authors": "Won, M. R., Choi, E. J., Ko, E., Um, Y. J. & Choi, Y. J.", "journal": "International Journal of Geriatric Psychiatry, 36(11)", "doi": None},
    {"year": 2021, "title": "Effects of Stress, Depression, and Problem Drinking on Suicidal Ideation among Korean Workers", "authors": "Choi, Y. J., Won, M. R. & Um, Y. J.", "journal": "International Journal of Mental Health Promotion, 23", "doi": None},
    {"year": 2021, "title": "Nursing students' extracurricular activity experiences of suicide prevention volunteering: A qualitative study", "authors": "Yoo, S. Y., Choi, E. J. & Choi, Y. J.", "journal": "Nurse Education Today, 102", "doi": None},
    {"year": 2021, "title": "Effects of a psychological first aid simulated training for pregnant flood victims on disaster relief worker's knowledge, competence, and self-efficacy", "authors": "Kang, J. Y. & Choi, Y. J.", "journal": "Applied Nursing Research, 57", "doi": None},
    # 2020
    {"year": 2020, "title": "The effect of employment status on people with a mental disability and on daily life satisfaction", "authors": "Um, Y. J. & Choi, Y. J.", "journal": "Current Psychology", "doi": None},
    {"year": 2020, "title": "Challenges and growth as a mental health professional from volunteering experiences in the community gambling awareness campaign", "authors": "Yoo, S. Y., Choi, Y. J. & Um, Y. J.", "journal": "International Journal of Mental Health Promotion, 22(2)", "doi": None},
    {"year": 2020, "title": "Debriefing model for psychological safety in nursing simulations: a qualitative study", "authors": "Ko, E. & Choi, Y. J.", "journal": "International Journal of Environmental Research and Public Health, 17(8)", "doi": None},
    {"year": 2020, "title": "The Mediating Role of Job Satisfaction in the Relationship between Disaster Relief Workers' Perception of Survivors' Rights and Their Performance of Human Rights Advocacy", "authors": "Choi, Y. J. & Ko, E.", "journal": "International Journal of Mental Health Promotion, 22", "doi": None},
    {"year": 2020, "title": "Bilingual gatekeepers' experiences of immigrant women's acculturative stress and mental health improvement in Korea: A qualitative analysis", "authors": "Choi, Y. J.", "journal": "Social Behavior and Personality, 48(9)", "doi": None},
    {"year": 2020, "title": "Psychological first-aid experiences of disaster health care workers: a qualitative analysis", "authors": "Choi, Y. J.", "journal": "Disaster Medicine and Public Health Preparedness, 14(4)", "doi": None},
    # 2019
    {"year": 2019, "title": "Relationships between smartphone dependency and aggression among middle school students", "authors": "Um, Y. J., Choi, Y. J. & Yoo, S. Y.", "journal": "International Journal of Environmental Research and Public Health, 16(19)", "doi": None},
    {"year": 2019, "title": "Nurses' Positive Experiences in Caring for Older Adults With Dementia: A Qualitative Analysis", "authors": "Choi, Y. J. & Choi, H. B.", "journal": "Journal of Gerontological Nursing, 45(1)", "doi": None},
    {"year": 2019, "title": "Nursing competency and educational needs for clinical practice of Korean nurses", "authors": "Kim, S. O. & Choi, Y. J.", "journal": "Nurse Education in Practice, 34", "doi": None},
    # 2018
    {"year": 2018, "title": "Relationships of substance use and sexual behavior of female junior high school students in Korea", "authors": "Lee, G. Y., Song, S. H. & Choi, Y. J.", "journal": "Journal of Child & Adolescent Substance Abuse, 27(5-6)", "doi": None},
    {"year": 2018, "title": "Associations among elder abuse, depression and PTSD in South Korean older adults", "authors": "Choi, Y. J., O'Donnell, M., Choi, H. B., Jung, H. S. & Cowlishaw, S.", "journal": "International Journal of Environmental Research and Public Health, 15(9)", "doi": None},
    {"year": 2018, "title": "Three-dimensional needs of standardized patients in nursing simulations and collaboration strategies: A qualitative analysis", "authors": "Jin, H. R. & Choi, Y. J.", "journal": "Nurse Education Today, 68", "doi": None},
    {"year": 2018, "title": "Disaster reintegration model: a qualitative analysis on developing Korean disaster mental health support model", "authors": "Choi, Y. J., Choi, H. B. & O'Donnell, M.", "journal": "International Journal of Environmental Research and Public Health, 15(2)", "doi": None},
    {"year": 2018, "title": "The value of psychosocial group activity in nursing education: A qualitative analysis", "authors": "Choi, Y. J.", "journal": "Nurse Education Today, 64", "doi": None},
    # 2017
    {"year": 2017, "title": "Effects of a program to improve mental health literacy for married immigrant women in Korea", "authors": "Choi, Y. J.", "journal": "Archives of Psychiatric Nursing, 31(4)", "doi": None},
    {"year": 2017, "title": "Analysis of Korean adolescents' sexual experience and substance use", "authors": "Lee, G. Y. & Choi, Y. J.", "journal": "Social Behavior and Personality, 45(5)", "doi": None},
    {"year": 2017, "title": "Family stress and coping from hospitalization of clients with severe alcohol use disorder in Korea", "authors": "Park, G. H. & Choi, Y. J.", "journal": "Journal of Addictions Nursing, 28(1)", "doi": None},
    {"year": 2017, "title": "Factors associated with perceived depression of Korean adults: secondary data from the Korean Community Health Survey", "authors": "Won, M. R., Ahn, M. S. & Choi, Y. J.", "journal": "Community Mental Health Journal, 53", "doi": None},
    {"year": 2017, "title": "Undergraduate nursing student mentors' experiences of peer mentoring in Korea: A qualitative analysis", "authors": "Won, M. R. & Choi, Y. J.", "journal": "Nurse Education Today, 51", "doi": None},
    # 2016
    {"year": 2016, "title": "Immigrant women's acculturation stress and coping strategies in Korea: A qualitative analysis", "authors": "Choi, Y. J.", "journal": "International Journal of Intercultural Relations, 55", "doi": None},
    {"year": 2016, "title": "Evaluation of a program on self-esteem and ego-identity for Korean nursing students", "authors": "Choi, Y. J.", "journal": "Nursing & Health Sciences, 18(3)", "doi": None},
    {"year": 2016, "title": "Associations among acculturation stress, mental health literacy, and mental health of married immigrant women in Korea", "authors": "Choi, Y. J. & Park, G. H.", "journal": "International Journal of Mental Health Promotion, 18(4)", "doi": None},
    {"year": 2016, "title": "Undergraduate students' experiences of an integrated psychiatric nursing curriculum in Korea", "authors": "Choi, Y. J.", "journal": "Issues in Mental Health Nursing, 37(8)", "doi": None},
    {"year": 2016, "title": "Effects of an obesity management mentoring program for Korean children", "authors": "Lee, G. Y. & Choi, Y. J.", "journal": "Applied Nursing Research, 31", "doi": None},
    {"year": 2016, "title": "Mental health problems and acculturative issues among married immigrant women in Korea: A qualitative study", "authors": "Choi, Y. J.", "journal": "Women & Health, 56(6)", "doi": None},
    # 2015
    {"year": 2015, "title": "Association of school, family, and mental health characteristics with suicidal ideation among Korean adolescents", "authors": "Lee, G. Y. & Choi, Y. J.", "journal": "Research in Nursing & Health, 38(4)", "doi": None},
    {"year": 2015, "title": "Mobile phone overuse among elementary school students in Korea: Factors associated with mobile phone use as a behavior addiction", "authors": "Kim, R., Lee, K. J. & Choi, Y. J.", "journal": "Journal of Addictions Nursing, 26(2)", "doi": None},
    {"year": 2015, "title": "The impact of gender, culture, and society on Korean women's mental health", "authors": "Choi, Y. J.", "journal": "Social Behavior and Personality, 43(4)", "doi": None},
    {"year": 2015, "title": "Efficacy of adjunctive treatments added to olanzapine or clozapine for weight control in patients with schizophrenia: a systematic review and meta-analysis", "authors": "Choi, Y. J.", "journal": "The Scientific World Journal, 2015", "doi": None},
    # 2014 and earlier
    {"year": 2014, "title": "Phases of shopping addiction evidenced by experiences of compulsive buyers", "authors": "Sohn, S. H. & Choi, Y. J.", "journal": "International Journal of Mental Health and Addiction, 12", "doi": None},
    {"year": 2013, "title": "Are Koreans prepared for the rapid increase of the single-household elderly? Life satisfaction and depression of the single-household elderly in Korea", "authors": "Won, M. R. & Choi, Y. J.", "journal": "The Scientific World Journal, 2013", "doi": None},
    {"year": 2013, "title": "Standardized patients for Korean psychiatric nursing student simulations", "authors": "Choi, Y. J.", "journal": "Clinical Simulation in Nursing, 9(9)", "doi": None},
    {"year": 2013, "title": "A pilot study on effects of a group program using recreational therapy to improve interpersonal relationships for undergraduate nursing students", "authors": "Choi, Y. J. & Won, M. R.", "journal": "Archives of Psychiatric Nursing, 27(1)", "doi": None},
    {"year": 2012, "title": "A model of compulsive buying: Dysfunctional beliefs and self-regulation of compulsive buyers", "authors": "Sohn, S. H. & Choi, Y. J.", "journal": "Social Behavior and Personality, 40(10)", "doi": None},
    {"year": 2012, "title": "Exploring experiences of psychiatric nursing simulations using standardized patients for undergraduate students", "authors": "Choi, Y. J.", "journal": "Asian Nursing Research, 6(3)", "doi": None},
    {"year": 2012, "title": "Effects of an emotion management nursing program for patients with schizophrenia", "authors": "Won, M. R., Lee, K. J., Lee, J. H. & Choi, Y. J.", "journal": "Archives of Psychiatric Nursing, 26(1)", "doi": None},
    {"year": 2010, "title": "The effect of an anger management program for family members of patients with alcohol use disorders", "authors": "Son, J. Y. & Choi, Y. J.", "journal": "Archives of Psychiatric Nursing, 24(1)", "doi": None},
    {"year": 2009, "title": "Efficacy of treatments for patients with obsessive-compulsive disorder: A systematic review", "authors": "Choi, Y. J.", "journal": "Journal of the American Academy of Nurse Practitioners, 21(4)", "doi": None},
    {"year": 2008, "title": "Experiences and challenges of informal caregiving for Korean immigrants", "authors": "Han, H. R., Choi, Y. J., Kim, M. T., Lee, J. E. & Kim, K. B.", "journal": "Journal of Advanced Nursing, 63(5)", "doi": None},
    {"year": 2007, "title": "Evidence-based nursing: effects of a structured nursing program for the health promotion of Korean women with Hwa-Byung", "authors": "Choi, Y. J. & Lee, K. J.", "journal": "Archives of Psychiatric Nursing, 21(1)", "doi": None},
]

COPYRIGHTS = [
    "재난경험자를 위한 마음 치유 기술",
    "재난구호자를 위한 심리적 인명구조술",
    "Psychological Recovery Skills for Disaster Survivors",
    "Psychological Life Support for Disaster Relief Workers",
    "기능성 게임 기반 심리적 응급처치 교육 프로그램 — 지진",
    "기능성 게임 기반 심리적 응급처치 교육 프로그램 — 화재",
    "기능성 게임 기반 심리적 응급처치 교육 프로그램 — 풍수해",
    "기능성 게임 기반 심리적 응급처치 교육 프로그램 — 감염병",
]


def _articles_by_year():
    result = OrderedDict()
    all_pubs = ARTICLES + load_extra_pubs()
    for pub in sorted(all_pubs, key=lambda x: -x["year"]):
        result.setdefault(pub["year"], []).append(pub)
    return result

# ─── Public routes ───────────────────────────────────────────
@app.route("/")
def home():
    recent = sorted(ARTICLES, key=lambda x: -x["year"])[:5]
    return render_template("home.html", research_topics=RESEARCH_TOPICS, recent_pubs=recent)

@app.route("/research")
def research():
    return render_template("research.html", research_topics=RESEARCH_TOPICS)

@app.route("/team")
def team():
    return render_template("team.html", professor=PROFESSOR, team=TEAM)

@app.route("/publications")
def publications():
    by_year = _articles_by_year()
    return render_template("publications.html", publications_by_year=by_year,
                           pub_years=list(by_year.keys()), copyrights=COPYRIGHTS,
                           current_year=datetime.now().year)

@app.route("/publications/new", methods=["POST"])
@login_required
def publications_new():
    title = request.form.get('title','').strip()
    if not title: return redirect(url_for('publications'))
    try:
        year = int(request.form.get('year', datetime.now().year))
    except ValueError:
        year = datetime.now().year
    doi_raw = request.form.get('doi','').strip()
    entry = {
        'year': year,
        'title': title,
        'authors': request.form.get('authors','').strip(),
        'journal': request.form.get('journal','').strip(),
        'doi': doi_raw if doi_raw else None,
    }
    extra = load_extra_pubs()
    extra.append(entry)
    save_extra_pubs(extra)
    return redirect(url_for('publications'))

@app.route("/apps")
def apps():
    all_apps = APPS + load_extra_apps()
    return render_template("apps.html", apps=all_apps)

@app.route("/apps/new", methods=["POST"])
@login_required
def apps_new():
    name = request.form.get('name','').strip()
    if not name: return redirect(url_for('apps'))
    key = re.sub(r'[^a-z0-9_]','', name.lower().replace(' ','_'))
    if not key: key = 'app'
    extra = load_extra_apps()
    taken = {a['key'] for a in APPS} | {a['key'] for a in extra}
    base, n = key, 2
    while key in taken: key = f"{base}_{n}"; n += 1
    color_map = {
        'teal':   'linear-gradient(135deg,#0F6B6B 0%,#1ec0c0 100%)',
        'blue':   'linear-gradient(135deg,#1a237e 0%,#5c6bc0 100%)',
        'purple': 'linear-gradient(135deg,#4a148c 0%,#9c27b0 100%)',
        'green':  'linear-gradient(135deg,#1b5e20 0%,#66bb6a 100%)',
        'orange': 'linear-gradient(135deg,#e65100 0%,#ff9800 100%)',
    }
    gradient = color_map.get(request.form.get('color','teal'), color_map['teal'])
    app_entry = {'key':key,'icon':request.form.get('icon','📱'),'gradient':gradient,
        'name':name,'full_name':request.form.get('full_name',''),'label':request.form.get('label',''),
        'desc_kr':'','desc_en':request.form.get('desc_en',''),'tags':[],'screenshot':None,
        'content_img_kr':None,'content_img_en':None,'dl_kr':None,'dl_en':None,'subsections':[],
        'created_at':datetime.now().isoformat()[:10]}
    extra.append(app_entry)
    save_extra_apps(extra)
    return redirect(url_for('app_detail', key=key))

@app.route("/apps/<key>")
def app_detail(key):
    all_apps = APPS + load_extra_apps()
    app_data = next((a for a in all_apps if a.get('key')==key), None)
    if not app_data: return redirect(url_for('apps'))
    return render_template("app_detail.html", app=app_data)

@app.route("/contact", methods=["GET","POST"])
def contact():
    sent = False
    if request.method == "POST": sent = True
    return render_template("contact.html", message_sent=sent)

@app.route("/gallery")
def gallery():
    events = load_events()
    for ev in events:
        photos = event_photos(ev['key'])
        ev['photo_count'] = len(photos)
        ev['cover_photo'] = ev.get('cover') or (photos[0] if photos else None)
    return render_template("gallery.html", events=events)

@app.route("/gallery/new", methods=["POST"])
@login_required
def gallery_new():
    title = request.form.get('title','').strip()
    if not title: return redirect(url_for('gallery'))
    key = re.sub(r'[^a-z0-9_]','', title.lower().replace(' ','_').replace('(','').replace(')',''))
    if not key: key = 'event'
    events = load_events()
    existing = {e['key'] for e in events}
    base, n = key, 2
    while key in existing: key = f"{base}_{n}"; n += 1
    ev = {'key':key,'title':title,'date':request.form.get('date',''),
          'venue':request.form.get('venue',''),'description':request.form.get('description',''),
          'cover':None,'created_at':datetime.now().isoformat()[:10]}
    events.insert(0, ev)
    save_events(events)
    os.makedirs(os.path.join(GALLERY_FOLDER, key), exist_ok=True)
    return redirect(url_for('gallery_event', key=key))

@app.route("/gallery/<key>")
def gallery_event(key):
    events = load_events()
    ev = next((e for e in events if e['key']==key), None)
    if not ev: return redirect(url_for('gallery'))
    photos = event_photos(key)
    return render_template("gallery_event.html", event=ev, photos=photos)

@app.route("/gallery/<key>/upload", methods=["POST"])
def gallery_event_upload(key):
    events = load_events()
    ev = next((e for e in events if e['key']==key), None)
    if not ev: return redirect(url_for('gallery'))
    folder = os.path.join(GALLERY_FOLDER, key)
    os.makedirs(folder, exist_ok=True)
    changed = False
    for file in request.files.getlist('photo'):
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            if filename:
                file.save(os.path.join(folder, filename))
                if not ev.get('cover'): ev['cover'] = filename; changed = True
    if changed: save_events(events)
    return redirect(url_for('gallery_event', key=key))

@app.route("/gallery/<key>/delete/<filename>", methods=["POST"])
def gallery_event_delete(key, filename):
    safe = secure_filename(filename)
    path = os.path.join(GALLERY_FOLDER, key, safe)
    if os.path.exists(path): os.remove(path)
    events = load_events()
    ev = next((e for e in events if e['key']==key), None)
    if ev and ev.get('cover')==safe:
        remaining = event_photos(key)
        ev['cover'] = remaining[0] if remaining else None
        save_events(events)
    return redirect(url_for('gallery_event', key=key))

@app.route("/gallery/<key>/delete-event", methods=["POST"])
def gallery_delete_event(key):
    events = load_events()
    save_events([e for e in events if e['key']!=key])
    return redirect(url_for('gallery'))

# ─── Auth ────────────────────────────────────────────────────
RESEARCHER_ACCOUNTS = {
    "caupsynr@gmail.com":    "tsl2025!",
    "yunjungchoi@cau.ac.kr": "tsl2025!",
}

@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    if request.method == "POST":
        email    = request.form.get("email","").strip()
        password = request.form.get("password","").strip()
        if email in RESEARCHER_ACCOUNTS and RESEARCHER_ACCOUNTS[email]==password:
            session["researcher"] = email
            return redirect(url_for("portal"))
        error = "이메일 또는 비밀번호가 올바르지 않습니다."
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# 프로젝트 기반 포털
# ════════════════════════════════════════════════════

@app.route("/portal")
@login_required
def portal():
    email = session["researcher"]
    projects = sb("GET","projects",params=f"?researcher_email=eq.{email}&order=created_at.desc") or []
    for p in (projects if isinstance(projects,list) else []):
        pid = p.get("id","")
        pcs = sb("GET","project_participants",params=f"?project_id=eq.{pid}&select=id") or []
        mcs = sb("GET","measurements",params=f"?project_id=eq.{pid}&select=id") or []
        p["participant_count"] = len(pcs) if isinstance(pcs,list) else 0
        p["measurement_count"] = len(mcs) if isinstance(mcs,list) else 0
    all_p = sb("GET","project_participants",params="?select=id") or []
    all_m = sb("GET","measurements",params="?select=id") or []
    return render_template("portal.html",
        researcher=email,
        projects=projects if isinstance(projects,list) else [],
        total_participants=len(all_p) if isinstance(all_p,list) else 0,
        total_measurements=len(all_m) if isinstance(all_m,list) else 0)

@app.route("/portal/projects/new", methods=["POST"])
@login_required
def portal_project_new():
    sb("POST","projects",data={
        "name":            request.form.get("name","").strip(),
        "description":     request.form.get("description","").strip(),
        "researcher_email":session["researcher"],
        "app_type":        request.form.get("app_type","").strip(),
    })
    return redirect(url_for("portal"))

@app.route("/portal/projects/<project_id>")
@login_required
def portal_project(project_id):
    proj = sb("GET","projects",params=f"?id=eq.{project_id}")
    if not proj or not isinstance(proj,list): return redirect(url_for("portal"))
    project = proj[0]
    participants = sb("GET","project_participants",params=f"?project_id=eq.{project_id}&order=enrolled_at.desc") or []
    measurements_raw = sb("GET","measurements",params=f"?project_id=eq.{project_id}&order=measured_at.desc") or []
    variables = sb("GET","project_variables",params=f"?project_id=eq.{project_id}") or []
    p_map = {p["id"]: p["code"] for p in (participants if isinstance(participants,list) else [])}
    for m in (measurements_raw if isinstance(measurements_raw,list) else []):
        m["participant_code"] = p_map.get(m.get("participant_id",""),"")
    for p in (participants if isinstance(participants,list) else []):
        p["mcount"] = sum(1 for m in (measurements_raw if isinstance(measurements_raw,list) else []) if m.get("participant_id")==p["id"])
    return render_template("portal_project.html",
        project=project,
        participants=participants if isinstance(participants,list) else [],
        measurements=measurements_raw if isinstance(measurements_raw,list) else [],
        variables=variables if isinstance(variables,list) else [],
        researcher=session["researcher"])

@app.route("/portal/projects/<project_id>/delete", methods=["POST"])
@login_required
def portal_project_delete(project_id):
    sb("DELETE","measurements",params=f"?project_id=eq.{project_id}")
    sb("DELETE","project_participants",params=f"?project_id=eq.{project_id}")
    sb("DELETE","project_variables",params=f"?project_id=eq.{project_id}")
    sb("DELETE","projects",params=f"?id=eq.{project_id}")
    flash("프로젝트가 삭제됐습니다.")
    return redirect(url_for("portal"))

@app.route("/portal/projects/<project_id>/participants/add", methods=["POST"])
@login_required
def portal_project_add_participant(project_id):
    age_raw = request.form.get("age","").strip()
    sb("POST","project_participants",data={
        "project_id":  project_id,
        "code":        request.form.get("code","").strip(),
        "gender":      request.form.get("gender","").strip() or None,
        "age":         int(age_raw) if age_raw.isdigit() else None,
        "group_name":  request.form.get("group_name","").strip() or None,
    })
    return redirect(url_for("portal_project", project_id=project_id))

@app.route("/portal/projects/<project_id>/participants/<participant_id>/delete", methods=["POST"])
@login_required
def portal_project_delete_participant(project_id, participant_id):
    sb("DELETE","measurements",params=f"?participant_id=eq.{participant_id}")
    sb("DELETE","project_participants",params=f"?id=eq.{participant_id}")
    return redirect(url_for("portal_project", project_id=project_id))

@app.route("/portal/projects/<project_id>/participants/<participant_id>/edit", methods=["POST"])
@login_required
def portal_edit_participant(project_id, participant_id):
    age_raw = request.form.get("age","").strip()
    sb("PATCH","project_participants",
       data={"gender":request.form.get("gender","").strip() or None,
             "age":int(age_raw) if age_raw.isdigit() else None,
             "group_name":request.form.get("group_name","").strip() or None},
       params=f"?id=eq.{participant_id}")
    return redirect(url_for("portal_participant_detail", project_id=project_id, participant_id=participant_id))

@app.route("/portal/projects/<project_id>/participants/<participant_id>")
@login_required
def portal_participant_detail(project_id, participant_id):
    import math
    proj = sb("GET","projects",params=f"?id=eq.{project_id}")
    if not proj or not isinstance(proj,list): return redirect(url_for("portal"))
    p_list = sb("GET","project_participants",params=f"?id=eq.{participant_id}")
    if not p_list or not isinstance(p_list,list): return redirect(url_for("portal_project",project_id=project_id))
    participant = p_list[0]
    measurements = sb("GET","measurements",params=f"?participant_id=eq.{participant_id}&order=measured_at.asc") or []
    variables = sb("GET","project_variables",params=f"?project_id=eq.{project_id}") or []
    changes = {}
    if isinstance(measurements,list) and isinstance(variables,list):
        pre_data  = next((m["data"] for m in measurements if m.get("phase") in ["사전","pre","1회차","T1"]), None)
        post_data = next((m["data"] for m in measurements if m.get("phase") in ["사후","post","최종","T2"]), None)
        if pre_data and post_data:
            for v in variables:
                vn = v["name"]
                try:
                    pre_val = float(pre_data.get(vn,0))
                    post_val = float(post_data.get(vn,0))
                    changes[vn] = {"pre":pre_val,"post":post_val,"diff":round(post_val-pre_val,2),
                                   "label":v.get("label") or vn,"unit":v.get("unit","")}
                except: pass
    return render_template("portal_participant_detail.html",
        project=proj[0], participant=participant,
        measurements=measurements if isinstance(measurements,list) else [],
        variables=variables if isinstance(variables,list) else [],
        changes=changes, researcher=session["researcher"])

@app.route("/portal/projects/<project_id>/measurements/add", methods=["POST"])
@login_required
def portal_project_add_measurement(project_id):
    variables = sb("GET","project_variables",params=f"?project_id=eq.{project_id}") or []
    if variables and isinstance(variables,list):
        data_dict = {}
        for v in variables:
            val = request.form.get(f"var_{v['name']}","").strip()
            if val:
                try:    data_dict[v["name"]] = float(val) if v.get("var_type")=="number" else val
                except: data_dict[v["name"]] = val
    else:
        raw = request.form.get("data_json","").strip()
        try:    data_dict = json.loads(raw) if raw else {}
        except: data_dict = {"raw": raw}
    sb("POST","measurements",data={
        "project_id":     project_id,
        "participant_id": request.form.get("participant_id","").strip(),
        "phase":          request.form.get("phase","").strip() or None,
        "notes":          request.form.get("notes","").strip() or None,
        "data":           data_dict,
    })
    return redirect(url_for("portal_project", project_id=project_id))

@app.route("/portal/projects/<project_id>/measurements/<measurement_id>/delete", methods=["POST"])
@login_required
def portal_project_delete_measurement(project_id, measurement_id):
    sb("DELETE","measurements",params=f"?id=eq.{measurement_id}")
    return redirect(url_for("portal_project", project_id=project_id))

@app.route("/portal/projects/<project_id>/measurements/<measurement_id>/edit", methods=["POST"])
@login_required
def portal_edit_measurement(project_id, measurement_id):
    variables = sb("GET","project_variables",params=f"?project_id=eq.{project_id}") or []
    if variables and isinstance(variables,list):
        data_dict = {}
        for v in variables:
            val = request.form.get(f"var_{v['name']}","").strip()
            if val:
                try:    data_dict[v["name"]] = float(val) if v.get("var_type")=="number" else val
                except: data_dict[v["name"]] = val
    else:
        raw = request.form.get("data_json","").strip()
        try:    data_dict = json.loads(raw) if raw else {}
        except: data_dict = {"raw": raw}
    sb("PATCH","measurements",
       data={"phase":request.form.get("phase","").strip() or None,
             "notes":request.form.get("notes","").strip() or None,
             "data":data_dict},
       params=f"?id=eq.{measurement_id}")
    return redirect(url_for("portal_participant_detail", project_id=project_id,
                            participant_id=request.form.get("participant_id","")))

@app.route("/portal/projects/<project_id>/variables/add", methods=["POST"])
@login_required
def portal_project_add_variable(project_id):
    sb("POST","project_variables",data={
        "project_id": project_id,
        "name":       request.form.get("name","").strip(),
        "label":      request.form.get("label","").strip() or None,
        "var_type":   request.form.get("var_type","number"),
        "unit":       request.form.get("unit","").strip() or None,
    })
    return redirect(url_for("portal_project", project_id=project_id))

@app.route("/portal/projects/<project_id>/export")
@login_required
def portal_project_export(project_id):
    proj = sb("GET","projects",params=f"?id=eq.{project_id}")
    proj_name = proj[0]["name"] if proj and isinstance(proj,list) else "project"
    participants = sb("GET","project_participants",params=f"?project_id=eq.{project_id}") or []
    measurements = sb("GET","measurements",params=f"?project_id=eq.{project_id}&order=measured_at.desc") or []
    p_map = {p["id"]: p for p in (participants if isinstance(participants,list) else [])}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["participant_code","group","gender","age","phase","measured_at","notes","data"])
    for m in (measurements if isinstance(measurements,list) else []):
        p = p_map.get(m.get("participant_id",""), {})
        writer.writerow([p.get("code",""),p.get("group_name",""),p.get("gender",""),p.get("age",""),
                         m.get("phase",""),m.get("measured_at","")[:10],
                         m.get("notes",""),json.dumps(m.get("data",{}),ensure_ascii=False)])
    output.seek(0)
    safe = proj_name.replace(" ","_")
    return Response(output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition":f"attachment;filename={safe}_{datetime.now().strftime('%Y%m%d')}.csv"})

@app.route("/portal/projects/<project_id>/upload", methods=["POST"])
@login_required
def portal_project_upload(project_id):
    f = request.files.get("file")
    if not f or not f.filename:
        flash("파일을 선택해주세요.")
        return redirect(url_for("portal_project", project_id=project_id))
    fname = f.filename.lower()
    rows = []
    try:
        if fname.endswith(".csv"):
            import io as _io
            content = f.read().decode("utf-8-sig")
            reader = csv.DictReader(_io.StringIO(content))
            rows = list(reader)
        elif fname.endswith((".xlsx",".xls")):
            import tempfile, openpyxl
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            f.save(tmp.name)
            wb = openpyxl.load_workbook(tmp.name, read_only=True)
            ws = wb.active
            headers = [str(c.value or "").strip() for c in next(ws.iter_rows(max_row=1))]
            for row in ws.iter_rows(min_row=2, values_only=True):
                rows.append({headers[i]: (str(v).strip() if v is not None else "") for i,v in enumerate(row)})
            wb.close()
        else:
            flash("CSV 또는 Excel 파일만 업로드 가능해요.")
            return redirect(url_for("portal_project", project_id=project_id))
    except Exception as e:
        flash(f"파일 읽기 오류: {e}")
        return redirect(url_for("portal_project", project_id=project_id))
    variables = sb("GET","project_variables",params=f"?project_id=eq.{project_id}") or []
    var_names = [v["name"] for v in (variables if isinstance(variables,list) else [])]
    existing = sb("GET","project_participants",params=f"?project_id=eq.{project_id}") or []
    p_map = {p["code"]: p["id"] for p in (existing if isinstance(existing,list) else [])}
    added_p = added_m = errors = 0
    for row in rows:
        code = str(row.get("code") or row.get("참여자코드") or "").strip()
        if not code: errors+=1; continue
        if code not in p_map:
            age_raw = str(row.get("age") or row.get("나이") or "").strip()
            new_p = sb("POST","project_participants",data={
                "project_id":project_id,"code":code,
                "gender":str(row.get("gender") or row.get("성별") or "").strip() or None,
                "age":int(age_raw) if age_raw.isdigit() else None,
                "group_name":str(row.get("group") or row.get("그룹") or "").strip() or None,
            })
            if new_p and isinstance(new_p,list): p_map[code]=new_p[0]["id"]; added_p+=1
        pid = p_map.get(code)
        if not pid: errors+=1; continue
        phase = str(row.get("phase") or row.get("회차") or "").strip() or None
        notes = str(row.get("notes") or row.get("메모") or "").strip() or None
        data_dict = {}
        skip = {"code","참여자코드","gender","성별","age","나이","group","그룹","group_name","phase","회차","notes","메모"}
        for k,v in row.items():
            if k not in skip and v:
                try: data_dict[k]=float(v)
                except: data_dict[k]=v
        if data_dict:
            sb("POST","measurements",data={"project_id":project_id,"participant_id":pid,
                                           "phase":phase,"notes":notes,"data":data_dict})
            added_m+=1
    flash(f"업로드 완료 — 참여자 {added_p}명, 측정 {added_m}건 추가" + (f", {errors}행 오류" if errors else ""))
    return redirect(url_for("portal_project", project_id=project_id))

@app.route("/portal/projects/<project_id>/stats")
@login_required
def portal_project_stats(project_id):
    import math
    proj = sb("GET","projects",params=f"?id=eq.{project_id}")
    if not proj or not isinstance(proj,list): return redirect(url_for("portal"))
    measurements = sb("GET","measurements",params=f"?project_id=eq.{project_id}") or []
    variables    = sb("GET","project_variables",params=f"?project_id=eq.{project_id}") or []
    participants = sb("GET","project_participants",params=f"?project_id=eq.{project_id}") or []
    stats = {}
    if isinstance(measurements,list) and isinstance(variables,list):
        for v in variables:
            vn = v["name"]
            all_vals = []; by_phase = {}
            for m in measurements:
                val = m.get("data",{}).get(vn) if m.get("data") else None
                if val is not None:
                    try:
                        fval=float(val); all_vals.append(fval)
                        ph=m.get("phase","전체") or "전체"
                        by_phase.setdefault(ph,[]).append(fval)
                    except: pass
            def calc(vals):
                if not vals: return {}
                n=len(vals); avg=sum(vals)/n
                sd=math.sqrt(sum((x-avg)**2 for x in vals)/n) if n>1 else 0
                s=sorted(vals); med=s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2
                return {"n":n,"mean":round(avg,2),"sd":round(sd,2),"median":round(med,2),"min":round(min(vals),2),"max":round(max(vals),2)}
            outliers = []
            if len(all_vals)>=4:
                s=sorted(all_vals); q1=s[len(s)//4]; q3=s[3*len(s)//4]; iqr=q3-q1; lb,ub=q1-1.5*iqr,q3+1.5*iqr
                for m in measurements:
                    val=m.get("data",{}).get(vn) if m.get("data") else None
                    if val is not None:
                        try:
                            fval=float(val)
                            if fval<lb or fval>ub: outliers.append({"value":fval})
                        except: pass
            missing=[]
            phases=list({m.get("phase","") for m in measurements if m.get("phase")})
            for p in (participants if isinstance(participants,list) else []):
                p_ms=[m for m in measurements if m.get("participant_id")==p["id"]]
                for ph in phases:
                    if not any(m.get("phase")==ph and m.get("data",{}).get(vn) is not None for m in p_ms):
                        missing.append({"code":p["code"],"phase":ph})
            stats[vn]={"label":v.get("label") or vn,"unit":v.get("unit",""),
                       "overall":calc(all_vals),"by_phase":{ph:calc(vals) for ph,vals in by_phase.items()},
                       "outliers":outliers,"missing":missing}
    return render_template("portal_project_stats.html",
        project=proj[0],stats=stats,variables=variables if isinstance(variables,list) else [],
        researcher=session["researcher"])

@app.route("/portal/settings")
@login_required
def portal_settings():
    return render_template("portal_settings.html", researcher=session["researcher"])

@app.route("/portal/settings/password", methods=["POST"])
@login_required
def portal_change_password():
    current=request.form.get("current","").strip()
    new_pw=request.form.get("new_pw","").strip()
    confirm=request.form.get("confirm","").strip()
    email=session["researcher"]
    if RESEARCHER_ACCOUNTS.get(email)!=current: flash("현재 비밀번호가 틀렸어요."); return redirect(url_for("portal_settings"))
    if new_pw!=confirm: flash("새 비밀번호가 일치하지 않아요."); return redirect(url_for("portal_settings"))
    if len(new_pw)<6: flash("비밀번호는 6자 이상이어야 해요."); return redirect(url_for("portal_settings"))
    RESEARCHER_ACCOUNTS[email]=new_pw
    flash("비밀번호가 변경됐어요.")
    return redirect(url_for("portal_settings"))

@app.route("/portal/settings/add-account", methods=["POST"])
@login_required
def portal_add_account():
    new_email=request.form.get("email","").strip()
    new_pw=request.form.get("password","").strip()
    if not new_email or not new_pw: flash("이메일과 비밀번호를 입력해주세요."); return redirect(url_for("portal_settings"))
    if new_email in RESEARCHER_ACCOUNTS: flash("이미 존재하는 계정이에요."); return redirect(url_for("portal_settings"))
    RESEARCHER_ACCOUNTS[new_email]=new_pw
    flash(f"{new_email} 계정이 추가됐어요.")
    return redirect(url_for("portal_settings"))

@app.route("/portal/merge")
@login_required
def portal_merge():
    email=session["researcher"]
    projects=sb("GET","projects",params=f"?researcher_email=eq.{email}&order=created_at.desc") or []
    return render_template("portal_merge.html",researcher=email,
        projects=projects if isinstance(projects,list) else [])

@app.route("/portal/merge/preview", methods=["POST"])
@login_required
def portal_merge_preview():
    p1_id=request.form.get("project1_id",""); p2_id=request.form.get("project2_id","")
    if not p1_id or not p2_id or p1_id==p2_id: flash("서로 다른 프로젝트를 선택해주세요."); return redirect(url_for("portal_merge"))
    p1=sb("GET","projects",params=f"?id=eq.{p1_id}"); p2=sb("GET","projects",params=f"?id=eq.{p2_id}")
    p1_parts=sb("GET","project_participants",params=f"?project_id=eq.{p1_id}") or []
    p2_parts=sb("GET","project_participants",params=f"?project_id=eq.{p2_id}") or []
    p1_codes={p["code"] for p in (p1_parts if isinstance(p1_parts,list) else [])}
    p2_codes={p["code"] for p in (p2_parts if isinstance(p2_parts,list) else [])}
    return render_template("portal_merge.html",researcher=session["researcher"],
        projects=sb("GET","projects",params=f"?researcher_email=eq.{session['researcher']}&order=created_at.desc") or [],
        preview=True,project1=p1[0] if p1 else {},project2=p2[0] if p2 else {},
        common=sorted(p1_codes&p2_codes),only_p1=sorted(p1_codes-p2_codes),only_p2=sorted(p2_codes-p1_codes),
        p1_id=p1_id,p2_id=p2_id)

@app.route("/portal/merge/execute", methods=["POST"])
@login_required
def portal_merge_execute():
    p1_id=request.form.get("p1_id",""); p2_id=request.form.get("p2_id","")
    new_name=request.form.get("new_name","").strip() or "병합 프로젝트"
    new_proj=sb("POST","projects",data={"name":new_name,"description":f"병합: {p1_id[:8]}+{p2_id[:8]}",
        "researcher_email":session["researcher"]})
    if not new_proj or not isinstance(new_proj,list): flash("병합 실패"); return redirect(url_for("portal_merge"))
    new_pid=new_proj[0]["id"]
    all_vars={}
    for src in [p1_id,p2_id]:
        for v in (sb("GET","project_variables",params=f"?project_id=eq.{src}") or []):
            all_vars[v["name"]]=v
    for vn,v in all_vars.items():
        sb("POST","project_variables",data={"project_id":new_pid,"name":vn,
            "label":v.get("label"),"var_type":v.get("var_type","number"),"unit":v.get("unit")})
    p_code_map={}
    for src in [p1_id,p2_id]:
        for p in (sb("GET","project_participants",params=f"?project_id=eq.{src}") or []):
            if p["code"] not in p_code_map:
                new_p=sb("POST","project_participants",data={"project_id":new_pid,"code":p["code"],
                    "gender":p.get("gender"),"age":p.get("age"),"group_name":p.get("group_name")})
                if new_p and isinstance(new_p,list): p_code_map[p["code"]]=new_p[0]["id"]
    for src_pid in [p1_id,p2_id]:
        src_parts=sb("GET","project_participants",params=f"?project_id=eq.{src_pid}") or []
        src_map={p["id"]:p["code"] for p in (src_parts if isinstance(src_parts,list) else [])}
        tag="P1" if src_pid==p1_id else "P2"
        for m in (sb("GET","measurements",params=f"?project_id=eq.{src_pid}") or []):
            code=src_map.get(m.get("participant_id",""),"")
            new_pid2=p_code_map.get(code)
            if not new_pid2: continue
            sb("POST","measurements",data={"project_id":new_pid,"participant_id":new_pid2,
                "phase":f"[{tag}] {m.get('phase','')}" if m.get("phase") else tag,
                "notes":m.get("notes"),"data":m.get("data",{})})
    flash(f"병합 완료! '{new_name}' 프로젝트가 생성됐어요.")
    return redirect(url_for("portal_project", project_id=new_pid))

@app.route("/portal/all/participants")
@login_required
def portal_all_participants():
    participants=sb("GET","project_participants",params="?select=*,projects(name)&order=enrolled_at.desc") or []
    return render_template("portal_participants.html",researcher=session["researcher"],
        participants=participants if isinstance(participants,list) else [])

@app.route("/portal/all/sessions")
@login_required
def portal_all_sessions():
    sessions=sb("GET","sessions",params="?select=*,participants(code,app_type)&order=created_at.desc") or []
    return render_template("portal_sessions.html",researcher=session["researcher"],
        sessions=sessions if isinstance(sessions,list) else [])

@app.route("/api/sessions", methods=["POST"])
def api_receive_session():
    if request.headers.get("X-API-Key","")!=os.getenv("APP_API_KEY","tsl-app-key-2025"):
        return jsonify({"error":"Unauthorized"}),401
    payload=request.get_json(silent=True) or {}
    result=sb("POST","sessions",data={"participant_id":payload.get("participant_id"),
                                      "data":payload.get("data",{}),"notes":payload.get("notes","")})
    return jsonify({"ok":True,"result":result}),201

if __name__ == "__main__":
    app.run(debug=False)
