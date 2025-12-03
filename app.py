import os
from collections import Counter
from datetime import datetime
from flask import (
    Flask, render_template, redirect, url_for, flash,
    request, abort, send_from_directory
)
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
import spacy
from docx import Document
import PyPDF2

from config import Config
from models import db, User, Resume, JobPost, JobApplication
from forms import RegisterForm, LoginForm, UploadForm, JobForm

ALLOWED_EXT = {"pdf", "docx"}
MAX_FILES_PER_REQUEST = 100
nlp = spacy.load("en_core_web_sm")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config.get("UPLOAD_FOLDER", "uploads"), exist_ok=True)

    db.init_app(app)
    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ---------------------- SKILLS VOCAB (expanded) ---------------------- #
    SKILLS_VOCAB = [
        # Core programming & scripting
        "python","java","javascript","typescript","c++","c#","go","rust","ruby","php","swift","kotlin",
        "scala","perl","bash","powershell","r","matlab","objective-c","dart","assembly",
        # Web & frontend
        "html","css","sass","less","bootstrap","tailwind","react","react native","vue","angular","svelte",
        "next.js","nuxt","ember","jquery","webpack","rollup","vite","parcel",
        # Backend & frameworks
        "node.js","express","django","flask","fastapi","spring boot","laravel","symfony","asp.net","rails",
        # APIs & protocols
        "rest","graphql","grpc","websocket","oauth","jwt","openapi","swagger",
        # Databases
        "mysql","postgresql","sqlite","mongodb","redis","cassandra","dynamodb","cockroachdb","oracle","mssql",
        "elasticsearch","influxdb","timescaledb",
        # Cloud & infra
        "aws","azure","gcp","cloudflare","digitalocean","heroku","ibm cloud","oracle cloud",
        "ec2","s3","lambda","iam","vpc","rds","eks","gke","aks",
        # DevOps & CI/CD
        "docker","kubernetes","k8s","helm","terraform","ansible","chef","puppet","circleci","travis","github actions",
        "gitlab ci","jenkins","ci/cd","prometheus","grafana","monitoring","logstash","filebeat",
        # ML/AI/Data
        "machine learning","deep learning","data science","nlp","computer vision","pytorch","tensorflow","keras",
        "scikit-learn","xgboost","lightgbm","nlp","transformers","huggingface","openai","llm","chatgpt","gpt-4",
        "pandas","numpy","matplotlib","seaborn","plotly","data engineering","spark","hadoop","airflow","dbt",
        # MLOps & GenAI
        "mlops","sagemaker","bentoml","onnx","tensorRT","model serving","feature store","mlflow",
        # Testing & QA
        "pytest","junit","mocha","jest","selenium","cypress","robot framework","webdriverio","karma",
        # Security
        "cybersecurity","penetration testing","ethical hacking","owasp","sso","ssl","tls","firewall","siem","ids","ips",
        # Networking & OS
        "linux","ubuntu","centos","debian","windows server","tcp/ip","dns","dhcp","vpn","routing","iptables",
        # Mobile
        "android","ios","flutter","react native","swiftui","kotlin multiplatform",
        # Data / BI / Analytics
        "tableau","power bi","looker","metabase","bigquery","redshift","snowflake","data lake","etl","bi",
        # Low-code/No-code / Automation
        "rpa","uiPath","automation anywhere","makr","zapier","integromat",
        # Blockchain / Web3
        "blockchain","solidity","web3","ethereum","smart contracts","nft","dapp","metamask",
        # IoT & Embedded
        "arduino","raspberry pi","embedded c","iot","mqtt","zigbee","lorawan",
        # Project & product
        "agile","scrum","kanban","jira","confluence","product management","roadmap","stakeholder",
        # Design & UX
        "figma","adobe xd","photoshop","illustrator","ux research","ui design","wireframing","prototyping",
        # Marketing & growth
        "seo","sem","ppc","google analytics","content marketing","email marketing","social media",
        # HR & hiring
        "recruiting","talent acquisition","sourcing","onboarding","hris","performance management",
        # Soft skills (common keywords)
        "leadership","communication","teamwork","mentoring","coaching","time management","problem solving",
        # Add many more job-specific keywords and synonyms to broaden coverage
        # (Below is an extended list of commonly used technical and domain keywords)
        "microservices","monolith","serverless","edge computing","observability","scalability","high availability",
        "load balancing","caching","cdn","reverse proxy","nginx","apache","istio","linkerd","service mesh",
        "oauth2","saml","sso","account provisioning","ldap","active directory",
        "mobile testing","accessibility","a11y","internationalization","localization",
        "functional programming","object oriented","design patterns","clean architecture",
        "ci","cd","test automation","infrastructure as code","immutable infrastructure",
        "object storage","block storage","backup","disaster recovery","replication",
        "data modeling","schema design","normalization","denormalization",
        "etl pipeline","streaming","kafka","rabbitmq","pub/sub","kinesis","flink",
        "quantitative research","statistical modeling","time series","forecasting",
        "recommendation systems","nlp pipeline","named entity recognition","sentiment analysis",
        "reinforcement learning","computer graphics","opencv","image processing",
        "gpu programming","cuda","parallel computing","multithreading","concurrency",
        "performance tuning","profiling","benchmarking","latency","throughput",
        "billing","fintech","payments","stripe","paypal","klarna","banking",
        "healthcare it","ehr","hl7","fhir","medical imaging",
        "automation testing","test-driven development","bdd","tdd","acceptance criteria",
        "cms","drupal","wordpress","magento","shopify",
        "ecommerce","payment gateway","inventory management",
        "voice assistant","speech recognition","asr","tts",
        "graph databases","neo4j","query optimization","cypher",
        "vector databases","pinecone","weaviate","faiss","embeddings",
        "search","solr","lucene","full-text search","ranking","relevance",
        "business analysis","requirements gathering","use cases","user stories",
        "contract negotiation","vendor management","supply chain",
        "manufacturing","automation","scada","plc",
        "3d printing","cad","solidworks","autocad",
        # (You can expand further by adding company-specific or niche keywords)
    ]

    # ---------------------- UTILITIES ---------------------- #
    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

    def extract_text_from_pdf(path):
        text = ""
        try:
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
        except Exception:
            pass
        return text

    def extract_text_from_docx(path):
        try:
            doc = Document(path)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception:
            return ""

    def extract_text(path):
        if not os.path.exists(path):
            return ""
        ext = path.rsplit(".", 1)[1].lower()
        return extract_text_from_pdf(path) if ext == "pdf" else extract_text_from_docx(path)

    def detect_skills(text):
        lower = (text or "").lower()
        found = {s for s in SKILLS_VOCAB if s in lower}
        doc = nlp(text or "")
        tokens = [t.text.lower() for t in doc if not t.is_stop and t.is_alpha]
        freq = Counter(tokens)
        # return top matches sorted by token frequency (so relevant terms bubble up)
        return sorted(list(found), key=lambda s: -freq.get(s, 0))

    # ---------------------- ROUTES ---------------------- #
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        form = RegisterForm()
        if form.validate_on_submit():
            if User.query.filter_by(email=form.email.data).first():
                flash("Email already registered.", "warning")
                return redirect(url_for("login"))
            user = User(username=form.username.data, email=form.email.data, role=form.role.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))
        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                flash("Welcome back!", "success")
                return redirect(url_for("hr_dashboard" if user.role == "hr" else "candidate_dashboard"))
            flash("Invalid credentials.", "danger")
        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Logged out successfully.", "info")
        return redirect(url_for("index"))

    # -------- Candidate Dashboard -------- #
    @app.route("/candidate", methods=["GET", "POST"])
    @login_required
    def candidate_dashboard():
        if current_user.role != "candidate":
            abort(403)
        form = UploadForm()
        resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.created_at.desc()).all()
        applications = JobApplication.query.filter_by(candidate_id=current_user.id).order_by(JobApplication.created_at.desc()).all()
        return render_template("candidate_dashboard.html", resumes=resumes, form=form, applications=applications)

    @app.route("/upload", methods=["POST"])
    @login_required
    def upload():
        if current_user.role != "candidate":
            abort(403)

        files = request.files.getlist("file")
        if not files:
            flash("No files selected!", "warning")
            return redirect(url_for("candidate_dashboard"))

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)
                text = extract_text(filepath)
                skills = detect_skills(text)
                resume = Resume(
                    user_id=current_user.id,
                    filename=filename,
                    text=text[:10000],
                    detected_skills=",".join(skills),
                    created_at=datetime.utcnow()
                )
                db.session.add(resume)
        db.session.commit()
        flash("✅ Resume(s) uploaded and analyzed successfully!", "success")
        return redirect(url_for("candidate_dashboard"))

    @app.route("/apply_job", methods=["POST"])
    @login_required
    def apply_job():
        if current_user.role != "candidate":
            abort(403)

        job_id = request.form.get("job_id")
        file = request.files.get("file")
        if not job_id or not file or not allowed_file(file.filename):
            flash("Missing Job ID or invalid file.", "warning")
            return redirect(url_for("candidate_dashboard"))

        job = JobPost.query.filter_by(job_id=job_id).first()
        if not job:
            flash("Invalid Job ID.", "danger")
            return redirect(url_for("candidate_dashboard"))

        filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(path)

        text = extract_text(path)
        detected = detect_skills(text)
        req_skills = detect_skills(job.description)
        matched = set(detected).intersection(set(req_skills))
        score = round(len(matched) / len(req_skills) * 100, 1) if req_skills else 0

        application = JobApplication(
            job_id=job.id,
            candidate_id=current_user.id,
            resume_text=text[:10000],
            detected_skills=",".join(detected),
            score=score,
            created_at=datetime.utcnow()
        )
        db.session.add(application)
        db.session.commit()
        flash(f"✅ Applied successfully for {job.title}! ATS Score: {score}%", "success")
        return redirect(url_for("candidate_dashboard"))

    @app.route("/uploads/<filename>")
    @login_required
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # ---------------- HR Dashboard ---------------- #
    @app.route("/hr", methods=["GET", "POST"])
    @login_required
    def hr_dashboard():
        if current_user.role != "hr":
            abort(403)

        job_form = JobForm()
        bulk_form = UploadForm()

        # Job create
        if job_form.validate_on_submit() and 'title' in request.form:
            timestamp = int(datetime.utcnow().timestamp())
            job_id = f"JOB-{timestamp}"
            job = JobPost(
                job_id=job_id,
                title=job_form.title.data,
                description=job_form.description.data,
                hr_id=current_user.id
            )
            db.session.add(job)
            db.session.commit()
            flash(f"Job created successfully! Job ID: {job_id}", "success")
            return redirect(url_for("hr_dashboard"))

        # Bulk upload resumes for a specific job description
        if bulk_form.validate_on_submit() and 'description' in request.form:
            files = request.files.getlist("file")
            description_text = request.form.get("description")
            # Optionally allow passing an existing job_id in form; if provided, associate directly
            target_job_id = request.form.get("target_job_id")
            if not files or not description_text:
                flash("Please provide job description and files.", "warning")
                return redirect(url_for("hr_dashboard"))

            # If HR provided an existing job id, link to that job, else create TEMP job or create new real job
            job_to_use = None
            if target_job_id:
                job_to_use = JobPost.query.filter_by(job_id=target_job_id, hr_id=current_user.id).first()
            if not job_to_use:
                # create a TEMP job entry (so results are tied to a JobPost)
                job_to_use = JobPost(
                    job_id=f"TEMP-{int(datetime.utcnow().timestamp())}",
                    title="Bulk Upload",
                    description=description_text,
                    hr_id=current_user.id
                )
                db.session.add(job_to_use)
                db.session.commit()

            processed_apps = []
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
                    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(path)
                    text = extract_text(path)
                    detected = detect_skills(text)
                    req_skills = detect_skills(description_text)
                    matched = set(detected).intersection(set(req_skills))
                    score = round(len(matched) / len(req_skills) * 100, 1) if req_skills else 0

                    # Create Resume record (uploaded by HR)
                    resume = Resume(
                        user_id=current_user.id,
                        filename=filename,
                        text=text[:10000],
                        detected_skills=",".join(detected),
                        created_at=datetime.utcnow()
                    )
                    db.session.add(resume)
                    db.session.commit()

                    # Save application and link to job_to_use
                    application = JobApplication(
                        job_id=job_to_use.id,
                        candidate_id=current_user.id,  # HR uploaded - placeholder; you'll replace with real candidate link later
                        resume_text=text[:10000],
                        detected_skills=f"{filename}||{','.join(detected)}",  # store filename||skills for template convenience
                        score=score,
                        shortlisted=(score >= 60),
                        created_at=datetime.utcnow()
                    )
                    db.session.add(application)
                    db.session.commit()
                    processed_apps.append((application, filename))
            flash(f"Bulk resumes analyzed successfully! {len(processed_apps)} processed.", "success")
            return redirect(url_for("hr_dashboard"))

        # Show jobs and bulk results (bulk results tied to JobPost.job_id starting with 'TEMP-' OR real jobs)
        jobs = JobPost.query.filter_by(hr_id=current_user.id).order_by(JobPost.created_at.desc()).all()

        # Show bulk results for TEMP jobs created by this HR
        # Join JobApplication -> JobPost and pick job_posts where job_post.job_id like 'TEMP-%'
        bulk_q = (
            db.session.query(JobApplication, JobPost)
            .join(JobPost, JobApplication.job_id == JobPost.id)
            .filter(JobPost.hr_id == current_user.id, JobPost.job_id.like("TEMP-%"))
            .order_by(JobApplication.created_at.desc())
            .all()
        )
        # Build processed list of dicts for template
        bulk_results = []
        for app_row, job_row in bulk_q:
            # detected_skills stored as 'filename||skill1,skill2'
            filename = None
            skills_str = ""
            if app_row.detected_skills and "||" in app_row.detected_skills:
                parts = app_row.detected_skills.split("||", 1)
                filename = parts[0]
                skills_str = parts[1]
            else:
                skills_str = app_row.detected_skills or ""
            bulk_results.append({
                "id": app_row.id,
                "job_id": job_row.job_id,
                "resume_filename": filename,
                "preview": (app_row.resume_text[:200] + "...") if app_row.resume_text else "",
                "skills": skills_str.split(",") if skills_str else [],
                "score": app_row.score,
                "shortlisted": app_row.shortlisted,
                "created_at": app_row.created_at
            })

        return render_template(
            "hr_dashboard.html",
            job_form=job_form,
            bulk_form=bulk_form,
            jobs=jobs,
            bulk_results=bulk_results
        )

    # -------------- View candidates for a given job --------------
    @app.route("/hr/job/<job_id>/candidates")
    @login_required
    def view_candidates(job_id):
        if current_user.role != "hr":
            abort(403)
        job = JobPost.query.filter_by(job_id=job_id, hr_id=current_user.id).first_or_404()
        apps = JobApplication.query.filter_by(job_id=job.id).order_by(JobApplication.created_at.desc()).all()

        # build simplified application view data
        processed = []
        for a in apps:
            # try to find filename if stored in detected_skills
            filename = None
            skills = []
            if a.detected_skills and "||" in a.detected_skills:
                fn, skills_str = a.detected_skills.split("||", 1)
                filename = fn
                skills = skills_str.split(",") if skills_str else []
            else:
                skills = (a.detected_skills or "").split(",") if a.detected_skills else []
            # Try to get candidate user (might be HR id if bulk uploaded)
            cand_user = None
            if a.candidate_id:
                cand_user = User.query.get(a.candidate_id)
            processed.append({
                "id": a.id,
                "candidate": cand_user.username if cand_user else "N/A",
                "email": cand_user.email if cand_user else "N/A",
                "filename": filename,
                "preview": (a.resume_text[:200] + "...") if a.resume_text else "",
                "skills": skills,
                "score": a.score,
                "shortlisted": a.shortlisted,
                "created_at": a.created_at
            })
        return render_template("hr_candidates.html", job=job, applications=processed)
    # -------------- Bulk Results (Separate Page) --------------
    @app.route("/hr/bulk_results")
    @login_required
    def bulk_results_page():
        if current_user.role != "hr":
            abort(403)

        # Fetch TEMP job’s bulk results
        bulk_q = (
            db.session.query(JobApplication, JobPost)
            .join(JobPost, JobApplication.job_id == JobPost.id)
            .filter(JobPost.hr_id == current_user.id, JobPost.job_id.like("TEMP-%"))
            .order_by(JobApplication.created_at.desc())
            .all()
        )

        results = []
        for app_row, job_row in bulk_q:
            filename = None
            skills_str = ""
            if app_row.detected_skills and "||" in app_row.detected_skills:
                parts = app_row.detected_skills.split("||", 1)
                filename = parts[0]
                skills_str = parts[1]

            results.append({
                "id": app_row.id,
                "job_id": job_row.job_id,
                "resume_filename": filename,
                "score": app_row.score,
                "shortlisted": app_row.shortlisted,
                "preview": (app_row.resume_text[:200] + "...") if app_row.resume_text else "",
                "skills": skills_str.split(",") if skills_str else [],
                "created_at": app_row.created_at
            })

        return render_template("bulk_results.html", results=results)



    # -------------- Edit job (GET form / POST update) --------------
    @app.route("/hr/job/<job_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_job(job_id):
        if current_user.role != "hr":
            abort(403)
        job = JobPost.query.filter_by(job_id=job_id, hr_id=current_user.id).first_or_404()
        form = JobForm(obj=job)
        if form.validate_on_submit():
            job.title = form.title.data
            job.description = form.description.data
            db.session.commit()
            flash("Job updated successfully.", "success")
            return redirect(url_for("hr_dashboard"))
        # pre-populate and show edit page (reuse hr_dashboard but show edit modal or separate template)
        return render_template("hr_edit_job.html", form=form, job=job)

    # -------------- Delete job --------------
    @app.route("/hr/job/<job_id>/delete", methods=["POST"])
    @login_required
    def delete_job(job_id):
        if current_user.role != "hr":
            abort(403)
        job = JobPost.query.filter_by(job_id=job_id, hr_id=current_user.id).first_or_404()

        # Deleting a job will NOT delete candidate resumes from uploads folder, but will remove job row
        # and job applications: remove JobApplication rows linked to this job
        JobApplication.query.filter_by(job_id=job.id).delete()
        db.session.delete(job)
        db.session.commit()
        flash(f"Job {job_id} and its applications have been deleted.", "info")
        return redirect(url_for("hr_dashboard"))

    # ---------------------- SAFE DB INIT ---------------------- #
    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)