/**
 * IRecruit AI Resume Intelligence - Client Application
 * Handles authentication, file uploads, analysis execution, dashboard history,
 * anonymous claim workflows, and reactive UI updates.
 */

(function () {
  "use strict";

  // Application State
  const state = {
    token: localStorage.getItem("irecruit_token") || null,
    user: null,
    selectedFile: null,
    activeInputTab: "upload",
    authMode: "login",
    latestAnonymousToken: sessionStorage.getItem("irecruit_anon_token") || null,
    currentAnalysis: null,
  };

  // Sample JD for quick demonstration
  const SAMPLE_JD = `Senior Backend Engineer (Python / FastAPI)
Role Overview:
We are seeking an experienced Backend Engineer to design scalable microservices and data pipelines.

Requirements:
- 4+ years of professional experience in Python, FastAPI, and asynchronous programming.
- Strong proficiency with PostgreSQL, relational database modeling, and SQLAlchemy.
- Hands-on expertise in Docker containerization and CI/CD pipelines.
- Deep understanding of RESTful API design, authentication, and application security.

Preferred Qualifications:
- Experience with Cloud deployment (AWS / GCP) and Kubernetes.
- Background in NLP, semantic search, or AI/LLM orchestration.
- Bachelor's degree in Computer Science or equivalent practical experience.`;

  // DOM Elements
  const elements = {
    // Navigation & Auth
    logoLink: document.getElementById("logoLink"),
    navWorkbench: document.getElementById("navWorkbench"),
    navDashboard: document.getElementById("navDashboard"),
    mobileMenuBtn: document.getElementById("mobileMenuBtn"),
    navLinks: document.getElementById("navLinks"),
    guestActions: document.getElementById("guestActions"),
    userActions: document.getElementById("userActions"),
    userGreeting: document.getElementById("userGreeting"),
    openLoginBtn: document.getElementById("openLoginBtn"),
    openRegisterBtn: document.getElementById("openRegisterBtn"),
    signOutBtn: document.getElementById("signOutBtn"),

    // Workbench Inputs
    tabFileUpload: document.getElementById("tabFileUpload"),
    tabTextPaste: document.getElementById("tabTextPaste"),
    panelFileUpload: document.getElementById("panelFileUpload"),
    panelTextPaste: document.getElementById("panelTextPaste"),
    dropzone: document.getElementById("dropzone"),
    resumeFileInput: document.getElementById("resumeFileInput"),
    selectedFileInfo: document.getElementById("selectedFileInfo"),
    selectedFileName: document.getElementById("selectedFileName"),
    removeFileBtn: document.getElementById("removeFileBtn"),
    resumeTextInput: document.getElementById("resumeTextInput"),
    jdTextInput: document.getElementById("jdTextInput"),
    sampleJdBtn: document.getElementById("sampleJdBtn"),
    checkAtsAudit: document.getElementById("checkAtsAudit"),
    checkPiiMinimization: document.getElementById("checkPiiMinimization"),
    analyzeBtn: document.getElementById("analyzeBtn"),
    loadingOverlay: document.getElementById("loadingOverlay"),
    loadingStatusText: document.getElementById("loadingStatusText"),

    // Results Display
    resultsContainer: document.getElementById("resultsContainer"),
    overallGauge: document.getElementById("overallGauge"),
    overallScoreVal: document.getElementById("overallScoreVal"),
    overallGradeVal: document.getElementById("overallGradeVal"),
    componentsGrid: document.getElementById("componentsGrid"),
    evidenceList: document.getElementById("evidenceList"),
    atsAuditBlock: document.getElementById("atsAuditBlock"),
    atsAuditContent: document.getElementById("atsAuditContent"),
    recommendationsList: document.getElementById("recommendationsList"),
    anonymousClaimBanner: document.getElementById("anonymousClaimBanner"),
    claimNowBtn: document.getElementById("claimNowBtn"),

    // Dashboard
    dashboardSection: document.getElementById("dashboard"),
    statTotalAnalyses: document.getElementById("statTotalAnalyses"),
    statAvgScore: document.getElementById("statAvgScore"),
    statTopMissing: document.getElementById("statTopMissing"),
    statUsageCount: document.getElementById("statUsageCount"),
    historyTableBody: document.getElementById("historyTableBody"),
    refreshDashboardBtn: document.getElementById("refreshDashboardBtn"),

    // Auth Modal
    authModal: document.getElementById("authModal"),
    authModalTitle: document.getElementById("authModalTitle"),
    modalTabLogin: document.getElementById("modalTabLogin"),
    modalTabRegister: document.getElementById("modalTabRegister"),
    authForm: document.getElementById("authForm"),
    fullNameGroup: document.getElementById("fullNameGroup"),
    authFullName: document.getElementById("authFullName"),
    authEmail: document.getElementById("authEmail"),
    authPassword: document.getElementById("authPassword"),
    authErrorMessage: document.getElementById("authErrorMessage"),
    authSubmitBtn: document.getElementById("authSubmitBtn"),
    closeAuthModalBtn: document.getElementById("closeAuthModalBtn"),

    // Toast Container
    toastContainer: document.getElementById("toastContainer"),
  };

  /* =========================================================================
     API Helper Functions
     ========================================================================= */
  async function apiRequest(endpoint, options = {}) {
    const headers = options.headers || {};
    if (state.token) {
      headers["Authorization"] = `Bearer ${state.token}`;
    }

    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    const config = {
      ...options,
      headers,
    };

    try {
      const response = await fetch(`/api/v1${endpoint}`, config);
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorMsg = data.detail || data.message || `Request failed with status ${response.status}`;
        throw new Error(errorMsg);
      }
      return data;
    } catch (err) {
      throw err;
    }
  }

  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    const icon = type === "success" ? "✓" : type === "error" ? "⚠️" : "ℹ️";
    toast.innerHTML = `<span style="font-weight:bold;">${icon}</span><span>${message}</span>`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  /* =========================================================================
     Authentication & Session Handlers
     ========================================================================= */
  async function checkUserSession() {
    if (!state.token) {
      updateAuthUI(null);
      return;
    }

    try {
      const userData = await apiRequest("/auth/me");
      state.user = userData;
      updateAuthUI(userData);
    } catch (err) {
      console.warn("Session expired or invalid token:", err);
      signOut();
    }
  }

  function updateAuthUI(user) {
    if (user) {
      elements.guestActions.style.display = "none";
      elements.userActions.style.display = "flex";
      elements.userGreeting.textContent = `Hello, ${user.full_name || user.email.split("@")[0]}`;
    } else {
      elements.guestActions.style.display = "flex";
      elements.userActions.style.display = "none";
      elements.userGreeting.textContent = "";
    }
  }

  function openAuthModal(mode = "login") {
    state.authMode = mode;
    elements.authModal.style.display = "flex";
    elements.authErrorMessage.style.display = "none";
    elements.authErrorMessage.textContent = "";

    if (mode === "login") {
      elements.authModalTitle.textContent = "Sign In to IRecruit";
      elements.modalTabLogin.classList.add("active");
      elements.modalTabRegister.classList.remove("active");
      elements.fullNameGroup.style.display = "none";
      elements.authSubmitBtn.textContent = "Sign In";
    } else {
      elements.authModalTitle.textContent = "Create an Account";
      elements.modalTabLogin.classList.remove("active");
      elements.modalTabRegister.classList.add("active");
      elements.fullNameGroup.style.display = "block";
      elements.authSubmitBtn.textContent = "Create Account";
    }
  }

  function closeAuthModal() {
    elements.authModal.style.display = "none";
  }

  async function handleAuthSubmit(e) {
    e.preventDefault();
    elements.authErrorMessage.style.display = "none";
    elements.authSubmitBtn.disabled = true;
    elements.authSubmitBtn.textContent = "Processing...";

    const email = elements.authEmail.value.trim();
    const password = elements.authPassword.value;
    const fullName = elements.authFullName.value.trim();

    try {
      let authResponse;
      if (state.authMode === "login") {
        authResponse = await apiRequest("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
      } else {
        authResponse = await apiRequest("/auth/register", {
          method: "POST",
          body: JSON.stringify({ email, password, full_name: fullName }),
        });
      }

      state.token = authResponse.access_token;
      localStorage.setItem("irecruit_token", state.token);
      showToast(state.authMode === "login" ? "Signed in successfully" : "Account registered successfully", "success");
      closeAuthModal();

      await checkUserSession();

      // If an anonymous analysis token is pending, offer to claim it
      if (state.latestAnonymousToken) {
        await claimAnonymousAnalysis(state.latestAnonymousToken);
      }
    } catch (err) {
      elements.authErrorMessage.textContent = err.message;
      elements.authErrorMessage.style.display = "block";
    } finally {
      elements.authSubmitBtn.disabled = false;
      elements.authSubmitBtn.textContent = state.authMode === "login" ? "Sign In" : "Create Account";
    }
  }

  function signOut() {
    state.token = null;
    state.user = null;
    localStorage.removeItem("irecruit_token");
    updateAuthUI(null);
    showToast("Signed out successfully", "info");
    elements.dashboardSection.style.display = "none";
    document.getElementById("workbench").scrollIntoView({ behavior: "smooth" });
  }

  /* =========================================================================
     Claim Workflow
     ========================================================================= */
  async function claimAnonymousAnalysis(claimToken) {
    if (!state.token) {
      openAuthModal("login");
      return;
    }

    const analysisId = state.currentAnalysis?.analysis_id;
    const sessionId = claimToken || state.currentAnalysis?.session_id || state.latestAnonymousToken;

    if (!analysisId || !sessionId) {
      showToast("No active anonymous analysis to claim.", "error");
      return;
    }

    try {
      const result = await apiRequest(`/analyses/${analysisId}/claim`, {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId }),
      });
      showToast("Analysis report saved to your dashboard!", "success");
      sessionStorage.removeItem("irecruit_anon_token");
      state.latestAnonymousToken = null;
      elements.anonymousClaimBanner.style.display = "none";

      if (elements.dashboardSection.style.display === "block") {
        loadDashboard();
      }
    } catch (err) {
      showToast(`Claim failed: ${err.message}`, "error");
    }
  }

  /* =========================================================================
     Analysis Execution & Rendering
     ========================================================================= */
  async function runAnalysis() {
    const jdText = elements.jdTextInput.value.trim();
    if (!jdText) {
      showToast("Please provide a Job Description to analyze against.", "error");
      elements.jdTextInput.focus();
      return;
    }

    elements.analyzeBtn.disabled = true;
    elements.loadingOverlay.style.display = "block";
    elements.resultsContainer.style.display = "none";

    try {
      let contentToSend = "";
      if (state.activeInputTab === "upload") {
        if (!state.selectedFile) {
          showToast("Please select a resume file (.pdf, .docx, or .txt) to upload.", "error");
          return;
        }

        if (state.selectedFile.name.endsWith(".txt")) {
          contentToSend = await readFileAsTextOrBase64(state.selectedFile);
        } else {
          // Upload PDF or DOCX to server to extract text cleanly
          const formData = new FormData();
          formData.append("file", state.selectedFile);
          const uploadRes = await apiRequest("/resumes/upload", {
            method: "POST",
            body: formData,
          });
          contentToSend = uploadRes.data?.extracted_text || (await readFileAsTextOrBase64(state.selectedFile));
        }
      } else {
        contentToSend = elements.resumeTextInput.value.trim();
        if (!contentToSend) {
          showToast("Please enter or paste your resume content.", "error");
          elements.resumeTextInput.focus();
          return;
        }
      }

      if (contentToSend.length < 20) {
        showToast("Resume content must be at least 20 characters.", "error");
        return;
      }

      const anonPayload = {
        resume_text: contentToSend,
        job_description_text: jdText,
        job_description: jdText,
        job_title: "Target Role",
        client_ip: "127.0.0.1",
        user_agent: navigator.userAgent || "Browser Client",
      };

      const anonResponse = await apiRequest("/analyses/anonymous", {
        method: "POST",
        body: JSON.stringify(anonPayload),
      });

      const resData = anonResponse.data || anonResponse;
      const analysisResult = resData;

      state.currentAnalysis = analysisResult;
      state.latestAnonymousToken = resData.session_id || resData.analysis_id;
      sessionStorage.setItem("irecruit_anon_token", state.latestAnonymousToken);

      // If user is already authenticated, automatically claim into their dashboard
      if (state.token && resData.analysis_id && resData.session_id) {
        try {
          await apiRequest(`/analyses/${resData.analysis_id}/claim`, {
            method: "POST",
            body: JSON.stringify({ session_id: resData.session_id }),
          });
          elements.anonymousClaimBanner.style.display = "none";
        } catch (claimErr) {
          console.warn("Auto-claim skipped:", claimErr);
        }
      } else {
        elements.anonymousClaimBanner.style.display = "flex";
      }

      renderAnalysisResults(analysisResult);
      showToast("Alignment analysis completed successfully!", "success");

      // Scroll to results
      elements.resultsContainer.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      console.error("Analysis failed:", err);
      showToast(`Analysis error: ${err.message}`, "error");
    } finally {
      elements.loadingOverlay.style.display = "none";
      elements.analyzeBtn.disabled = false;
    }
  }

  function readFileAsTextOrBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error("Failed to read file"));
      reader.readAsText(file);
    });
  }

  function renderAnalysisResults(analysis) {
    elements.resultsContainer.style.display = "block";

    // Overall Score & Grade
    const score = Math.round(analysis.overall_score || 0);
    elements.overallScoreVal.textContent = score;

    let grade = "C";
    if (score >= 90) grade = "A+";
    else if (score >= 80) grade = "A";
    else if (score >= 70) grade = "B";
    else if (score >= 60) grade = "C";
    else grade = "D";

    elements.overallGradeVal.textContent = `Grade ${grade}`;
    elements.overallGauge.style.setProperty("--score-pct", score);

    // Component Scores
    elements.componentsGrid.innerHTML = "";
    const components = analysis.component_scores || {};
    const componentLabels = {
      required_skills: { label: "Required Skills", weight: "40%" },
      preferred_skills: { label: "Preferred Skills", weight: "15%" },
      experience: { label: "Experience Alignment", weight: "25%" },
      domain_context: { label: "Domain Relevance", weight: "10%" },
      education: { label: "Education & Certs", weight: "10%" },
    };

    for (const [key, meta] of Object.entries(componentLabels)) {
      const compScore = Math.round(components[key] || 0);
      const card = document.createElement("div");
      card.className = "component-metric-card";
      card.innerHTML = `
        <div class="comp-header">
          <span>${meta.label}</span>
          <span style="color: var(--accent-cyan); font-weight: 700;">${compScore}%</span>
        </div>
        <div class="comp-progress-bg">
          <div class="comp-progress-bar" style="width: ${compScore}%; background: ${getScoreColor(compScore)};"></div>
        </div>
      `;
      elements.componentsGrid.appendChild(card);
    }

    // Evidence Verification Cards
    elements.evidenceList.innerHTML = "";
    const evidenceItems = analysis.evidence || [];
    if (evidenceItems.length === 0) {
      elements.evidenceList.innerHTML = `
        <div class="card-item" style="color: var(--text-muted); text-align: center; padding: 2rem;">
          No explicit requirements identified in this JD.
        </div>`;
    } else {
      evidenceItems.forEach((ev) => {
        const badgeClass = `badge-${(ev.classification || "missing").toLowerCase()}`;
        const card = document.createElement("div");
        card.className = "card-item";

        let quoteBlock = "";
        if (ev.has_evidence && ev.quote) {
          quoteBlock = `
            <div style="margin-top: 0.5rem; padding: 0.5rem 0.75rem; background: rgba(0, 0, 0, 0.3); border-left: 3px solid var(--accent-blue); border-radius: 4px; font-family: monospace; font-size: 0.85rem; color: #e2e8f0;">
              "${escapeHtml(ev.quote)}"
            </div>
          `;
        } else {
          quoteBlock = `
            <div style="margin-top: 0.5rem; font-style: italic; font-size: 0.85rem; color: var(--text-muted);">
              No supporting evidence was found in the submitted resume.
            </div>
          `;
        }

        card.innerHTML = `
          <div class="item-header">
            <span class="item-title">${escapeHtml(ev.requirement_text || "Requirement")}</span>
            <span class="badge ${badgeClass}">${ev.classification || "MISSING"}</span>
          </div>
          <div class="item-body">
            <div>Confidence: <strong>${Math.round((ev.confidence || 0) * 100)}%</strong> • Match Type: <strong>${ev.match_type || "Semantic"}</strong></div>
            ${quoteBlock}
          </div>
        `;
        elements.evidenceList.appendChild(card);
      });
    }

    // ATS Audit Block
    const ats = analysis.ats_compatibility || analysis.ats_audit;
    if (ats) {
      elements.atsAuditBlock.style.display = "block";
      const atsScore = Math.round(ats.overall_score || ats.ats_score || 0);

      elements.atsAuditContent.innerHTML = `
        <div class="card-item" style="border-left: 4px solid ${getScoreColor(atsScore)};">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <div style="font-weight: 700; font-size: 1.05rem;">Overall ATS Parser Friendliness</div>
            <div style="font-size: 1.25rem; font-weight: 800; color: ${getScoreColor(atsScore)};">${atsScore} / 100</div>
          </div>
          <p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
            ${escapeHtml(ats.summary || "Parsed and evaluated against common applicant tracking systems standard layouts.")}
          </p>
          <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
            ${(ats.findings || [ats.grade ? `Grade ${ats.grade}` : "ATS Verified", `${ats.issues_count || 0} issues detected`]).map(f => `<span class="badge" style="background: rgba(255,255,255,0.05); color: var(--text-secondary);">${escapeHtml(f)}</span>`).join("")}
          </div>
        </div>
      `;
    } else {
      elements.atsAuditBlock.style.display = "none";
    }

    // Recommendations List
    elements.recommendationsList.innerHTML = "";
    const recs = analysis.recommendations || [];
    if (recs.length === 0) {
      elements.recommendationsList.innerHTML = `
        <div class="card-item" style="color: var(--text-muted); text-align: center; padding: 1.5rem;">
          No direct phrasing enhancements recommended. Resume closely mirrors grounded evidence.
        </div>`;
    } else {
      recs.forEach((rec, idx) => {
        const item = document.createElement("div");
        item.className = "card-item";
        item.innerHTML = `
          <div class="item-header">
            <span class="item-title">Suggestion #${idx + 1}: ${escapeHtml(rec.title || "Targeted Improvement")}</span>
            <span class="badge" style="background: rgba(59, 130, 246, 0.2); color: var(--accent-cyan);">${rec.category || "Evidence Enhancement"}</span>
          </div>
          <div class="item-body">
            <p>${escapeHtml(rec.suggestion || rec.description || "")}</p>
          </div>
        `;
        elements.recommendationsList.appendChild(item);
      });
    }
  }

  function getScoreColor(val) {
    if (val >= 80) return "var(--color-success)";
    if (val >= 60) return "var(--color-warning)";
    return "var(--color-error)";
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  /* =========================================================================
     Dashboard History & Metrics
     ========================================================================= */
  async function loadDashboard() {
    if (!state.token) {
      openAuthModal("login");
      return;
    }

    try {
      const data = await apiRequest("/analyses/dashboard");

      elements.statTotalAnalyses.textContent = data.total_analyses || 0;
      elements.statAvgScore.textContent = `${Math.round(data.average_alignment_score || 0)}%`;
      elements.statTopMissing.textContent = data.top_missing_skill || "None detected";
      elements.statUsageCount.textContent = `${data.saved_count || 0} / ${data.free_tier_limit || 5}`;

      // Populate history table
      const history = data.recent_analyses || [];
      if (history.length === 0) {
        elements.historyTableBody.innerHTML = `
          <tr>
            <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">
              No saved analyses yet. Create an alignment analysis from the workbench to start tracking.
            </td>
          </tr>
        `;
      } else {
        elements.historyTableBody.innerHTML = history.map((item) => {
          const dateStr = new Date(item.created_at || Date.now()).toLocaleDateString();
          const score = Math.round(item.overall_score || 0);
          const atsScore = item.ats_score != null ? Math.round(item.ats_score) : "N/A";
          return `
            <tr>
              <td>${dateStr}</td>
              <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                ${escapeHtml(item.job_title || item.id)}
              </td>
              <td><span style="font-weight: 700; color: ${getScoreColor(score)}">${score}%</span></td>
              <td>${atsScore !== "N/A" ? `${atsScore}%` : "—"}</td>
              <td>
                <button type="button" class="btn btn-secondary" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;" onclick="window.viewSavedAnalysis('${item.id}')">View</button>
              </td>
            </tr>
          `;
        }).join("");
      }
    } catch (err) {
      showToast(`Failed to load dashboard: ${err.message}`, "error");
    }
  }

  window.viewSavedAnalysis = async function (analysisId) {
    try {
      const analysis = await apiRequest(`/analyses/${analysisId}`);
      renderAnalysisResults(analysis);
      elements.dashboardSection.style.display = "none";
      document.getElementById("workbench").scrollIntoView({ behavior: "smooth" });
      showToast(`Loaded analysis ${analysisId.substring(0, 8)}...`, "info");
    } catch (err) {
      showToast(`Failed to view analysis: ${err.message}`, "error");
    }
  };

  /* =========================================================================
     Event Listeners & Initialization
     ========================================================================= */
  function setupEventListeners() {
    // Navigation
    elements.navWorkbench.addEventListener("click", (e) => {
      e.preventDefault();
      elements.dashboardSection.style.display = "none";
      elements.navWorkbench.classList.add("active");
      elements.navDashboard.classList.remove("active");
      document.getElementById("workbench").scrollIntoView({ behavior: "smooth" });
    });

    elements.navDashboard.addEventListener("click", (e) => {
      e.preventDefault();
      if (!state.token) {
        openAuthModal("login");
        return;
      }
      elements.dashboardSection.style.display = "block";
      elements.navDashboard.classList.add("active");
      elements.navWorkbench.classList.remove("active");
      loadDashboard();
      elements.dashboardSection.scrollIntoView({ behavior: "smooth" });
    });

    elements.mobileMenuBtn.addEventListener("click", () => {
      const isOpen = elements.navLinks.classList.toggle("open");
      elements.mobileMenuBtn.setAttribute("aria-expanded", isOpen);
    });

    // Auth Buttons
    elements.openLoginBtn.addEventListener("click", () => openAuthModal("login"));
    elements.openRegisterBtn.addEventListener("click", () => openAuthModal("register"));
    elements.closeAuthModalBtn.addEventListener("click", closeAuthModal);
    elements.modalTabLogin.addEventListener("click", () => openAuthModal("login"));
    elements.modalTabRegister.addEventListener("click", () => openAuthModal("register"));
    elements.authForm.addEventListener("submit", handleAuthSubmit);
    elements.signOutBtn.addEventListener("click", signOut);

    // Workbench Input Tabs
    elements.tabFileUpload.addEventListener("click", () => {
      state.activeInputTab = "upload";
      elements.tabFileUpload.classList.add("active");
      elements.tabTextPaste.classList.remove("active");
      elements.panelFileUpload.style.display = "block";
      elements.panelTextPaste.style.display = "none";
    });

    elements.tabTextPaste.addEventListener("click", () => {
      state.activeInputTab = "paste";
      elements.tabTextPaste.classList.add("active");
      elements.tabFileUpload.classList.remove("active");
      elements.panelFileUpload.style.display = "none";
      elements.panelTextPaste.style.display = "block";
    });

    // File Dropzone Handling
    elements.dropzone.addEventListener("click", () => elements.resumeFileInput.click());
    elements.dropzone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        elements.resumeFileInput.click();
      }
    });

    elements.dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      elements.dropzone.classList.add("dragover");
    });

    elements.dropzone.addEventListener("dragleave", () => {
      elements.dropzone.classList.remove("dragover");
    });

    elements.dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      elements.dropzone.classList.remove("dragover");
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFileSelection(e.dataTransfer.files[0]);
      }
    });

    elements.resumeFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        handleFileSelection(e.target.files[0]);
      }
    });

    elements.removeFileBtn.addEventListener("click", () => {
      state.selectedFile = null;
      elements.resumeFileInput.value = "";
      elements.selectedFileInfo.style.display = "none";
      elements.dropzone.style.display = "block";
    });

    // Sample JD loader
    elements.sampleJdBtn.addEventListener("click", () => {
      elements.jdTextInput.value = SAMPLE_JD;
      showToast("Sample JD loaded into workbench", "info");
    });

    // Run Analysis Button
    elements.analyzeBtn.addEventListener("click", runAnalysis);

    // Claim Anonymous Report Button
    elements.claimNowBtn.addEventListener("click", () => {
      if (state.latestAnonymousToken) {
        claimAnonymousAnalysis(state.latestAnonymousToken);
      }
    });

    // Refresh Dashboard Button
    elements.refreshDashboardBtn.addEventListener("click", loadDashboard);

    // Escape Key to close modal
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && elements.authModal.style.display === "flex") {
        closeAuthModal();
      }
    });
  }

  function handleFileSelection(file) {
    const validExtensions = [".pdf", ".docx", ".txt"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!validExtensions.includes(ext)) {
      showToast("Invalid file type. Please upload a PDF, DOCX, or TXT document.", "error");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      showToast("File is too large. Maximum supported file size is 10MB.", "error");
      return;
    }

    state.selectedFile = file;
    elements.selectedFileName.textContent = `${file.name} (${Math.round(file.size / 1024)} KB)`;
    elements.dropzone.style.display = "none";
    elements.selectedFileInfo.style.display = "flex";
  }

  // Application Entrypoint
  async function init() {
    setupEventListeners();
    await checkUserSession();
  }

  document.addEventListener("DOMContentLoaded", init);
})();

