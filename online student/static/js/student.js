document.addEventListener('DOMContentLoaded', () => {
    // State management
    let performanceChart = null;
    let attendanceChart = null;

    // Toast Notification helper
    window.showToast = (message, type = 'success') => {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let icon = '✓';
        if (type === 'error') icon = '✕';
        if (type === 'warning') icon = '⚠';

        toast.innerHTML = `<span>${icon}</span> <div>${message}</div>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    };

    // Sidebar navigation & Mobile Toggle
    const sidebarItems = document.querySelectorAll('.sidebar-item');
    const contentSections = document.querySelectorAll('.content-section');
    const sidebar = document.getElementById('sidebar');
    const menuToggle = document.getElementById('menu-toggle');

    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });
    }

    sidebarItems.forEach(item => {
        const link = item.querySelector('a, button');
        if (!link || link.getAttribute('href') === '/api/auth/logout') return;

        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetSection = link.getAttribute('data-target');
            
            sidebarItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');

            contentSections.forEach(sec => {
                sec.classList.remove('active');
                if (sec.id === targetSection) {
                    sec.classList.add('active');
                }
            });

            // If mobile, close sidebar on link click
            if (window.innerWidth <= 992) {
                sidebar.classList.remove('active');
            }

            // Refresh data depending on section
            if (targetSection === 'sec-performance') {
                loadPerformanceData();
            } else if (targetSection === 'sec-attendance') {
                loadAttendanceData();
            }
        });
    });

    // Modal Helpers
    window.openModal = (modalId) => {
        document.getElementById(modalId).classList.add('active');
    };

    window.closeModal = (modalId) => {
        document.getElementById(modalId).classList.remove('active');
    };

    // Close modal when clicking overlay
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    });

    // ----------------------------------------------------
    // Section: Load Student Performance & Charts
    // ----------------------------------------------------
    const marksTableBody = document.querySelector('#student-marks-table tbody');

    function loadPerformanceData() {
        fetch('/api/student/marks')
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    const data = res.data;
                    marksTableBody.innerHTML = '';

                    // Update summary tiles
                    document.getElementById('perf-total-marks').innerText = `${data.total_obtained} / ${data.total_max}`;
                    document.getElementById('perf-pct').innerText = `${data.percentage}%`;
                    document.getElementById('perf-grade').innerText = data.grade;

                    const gradeBadge = document.getElementById('perf-grade');
                    gradeBadge.className = `badge badge-grade grade-${data.grade.replace('+', '-plus')}`;

                    if (data.subjects.length === 0) {
                        marksTableBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No marks have been recorded yet.</td></tr>`;
                        return;
                    }

                    data.subjects.forEach(sub => {
                        const subPct = Math.round(sub.marks_obtained / sub.max_marks * 100);
                        const subGrade = calculateGradeOffline(subPct);
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${sub.subject_name}</td>
                            <td>${sub.marks_obtained}</td>
                            <td>${sub.max_marks}</td>
                            <td><span class="badge grade-${subGrade.replace('+', '-plus')}">${subGrade}</span></td>
                        `;
                        marksTableBody.appendChild(tr);
                    });

                    renderPerformanceChart(data.subjects);
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to load performance details.', 'error');
            });
    }

    function renderPerformanceChart(subjects) {
        if (performanceChart) performanceChart.destroy();

        const ctx = document.getElementById('chart-student-perf').getContext('2d');
        const labels = subjects.map(s => s.subject_name);
        const marksObtained = subjects.map(s => s.marks_obtained);
        const maxMarks = subjects.map(s => s.max_marks);

        performanceChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Marks Obtained',
                        data: marksObtained,
                        backgroundColor: 'rgba(99, 102, 241, 0.6)',
                        borderColor: '#6366f1',
                        borderWidth: 1.5,
                        borderRadius: 6
                    },
                    {
                        label: 'Maximum Marks',
                        data: maxMarks,
                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                        borderColor: 'rgba(255, 255, 255, 0.2)',
                        borderWidth: 1.5,
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    x: {
                        ticks: { color: '#94a3b8' },
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: {
                        labels: { color: '#94a3b8', font: { family: 'Outfit' } }
                    }
                }
            }
        });
    }

    // ----------------------------------------------------
    // Section: Load Student Attendance & Charts
    // ----------------------------------------------------
    const attendanceTableBody = document.querySelector('#student-attendance-table tbody');

    function loadAttendanceData() {
        fetch('/api/student/attendance')
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    const data = res.data;
                    attendanceTableBody.innerHTML = '';

                    // Update summary tiles
                    document.getElementById('att-rate-summary').innerText = `${data.summary.rate}%`;
                    document.getElementById('att-total-days').innerText = data.summary.total;
                    document.getElementById('att-present-days').innerText = data.summary.counts.Present;

                    if (data.logs.length === 0) {
                        attendanceTableBody.innerHTML = `<tr><td colspan="2" style="text-align: center; color: var(--text-muted);">No attendance records found.</td></tr>`;
                        return;
                    }

                    data.logs.forEach(log => {
                        const tr = document.createElement('tr');
                        const statusClass = log.status.toLowerCase();
                        tr.innerHTML = `
                            <td>${log.date}</td>
                            <td><span class="badge badge-${statusClass}">${log.status}</span></td>
                        `;
                        attendanceTableBody.appendChild(tr);
                    });

                    renderAttendanceChart(data.summary.counts);
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to load attendance logs.', 'error');
            });
    }

    function renderAttendanceChart(counts) {
        if (attendanceChart) attendanceChart.destroy();

        const ctx = document.getElementById('chart-student-att').getContext('2d');
        attendanceChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Present', 'Absent', 'Late'],
                datasets: [{
                    data: [counts.Present, counts.Absent, counts.Late],
                    backgroundColor: ['#10b981', '#f43f5e', '#f59e0b'],
                    borderColor: 'rgba(255, 255, 255, 0.08)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', font: { family: 'Outfit' } }
                    }
                }
            }
        });
    }

    // ----------------------------------------------------
    // Section: Profile Management (Updating phone)
    // ----------------------------------------------------
    const updateProfileForm = document.getElementById('update-profile-form');
    if (updateProfileForm) {
        updateProfileForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const phone = document.getElementById('profile-phone-input').value.trim();

            fetch('/api/student/profile', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone })
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast(res.message, 'success');
                    closeModal('modal-edit-profile');
                    // Update value on screen
                    document.getElementById('profile-phone-display').innerText = phone || '—';
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to update phone number.', 'error');
            });
        });
    }

    function calculateGradeOffline(percentage) {
        if (percentage >= 90) return 'A+';
        if (percentage >= 80) return 'A';
        if (percentage >= 70) return 'B';
        if (percentage >= 60) return 'C';
        if (percentage >= 50) return 'D';
        if (percentage >= 40) return 'E';
        return 'F';
    }

    // ----------------------------------------------------
    // Section: Attendance Warning Banner
    // ----------------------------------------------------
    function checkAttendanceWarning() {
        fetch('/api/student/attendance')
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    const rate = parseFloat(res.data.summary.rate);
                    const banner = document.getElementById('attendance-warning-banner');
                    if (banner) {
                        if (rate < 75.0) {
                            banner.style.display = 'flex';
                            // Update dynamic rate value in message
                            const msg = banner.querySelector('.warning-banner-content p');
                            if (msg) {
                                msg.textContent = `Your current attendance is ${rate}%, which is below the required 75.0% threshold. Please coordinate with the administration immediately.`;
                            }
                        } else {
                            banner.style.display = 'none';
                        }
                    }
                }
            })
            .catch(err => console.error('Attendance warning check failed:', err));
    }

    // ----------------------------------------------------
    // Section: Student Noticeboard Feed
    // ----------------------------------------------------
    const studentNoticeList = document.getElementById('student-notice-list');

    function loadStudentNotices() {
        if (!studentNoticeList) return;
        fetch('/api/announcements')
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    studentNoticeList.innerHTML = '';
                    const list = res.data;
                    if (list.length === 0) {
                        studentNoticeList.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">No announcements from administration yet.</div>`;
                        return;
                    }
                    list.forEach(notice => {
                        const div = document.createElement('div');
                        div.className = 'announcement-card';
                        div.innerHTML = `
                            <div class="announcement-card-header">
                                <span class="announcement-title">${notice.title}</span>
                                <span class="announcement-date">${notice.date_posted}</span>
                            </div>
                            <p class="announcement-body">${notice.content}</p>
                        `;
                        studentNoticeList.appendChild(div);
                    });
                }
            })
            .catch(err => console.error('Failed to load notices:', err));
    }

    // ----------------------------------------------------
    // Section: Gemini AI Coach
    // ----------------------------------------------------
    window.loadAICoachFeedback = () => {
        const btn = document.getElementById('btn-load-ai');
        const content = document.getElementById('ai-coach-content');
        if (btn) {
            btn.disabled = true;
            btn.textContent = '🤖 Analyzing...';
        }
        if (content) {
            content.innerHTML = `
                <div style="display:flex; flex-direction:column; align-items:center; gap:12px; padding: 25px 0;">
                    <div style="border: 3px solid rgba(255,255,255,0.1); border-top: 3px solid var(--primary); border-radius: 50%; width: 28px; height: 28px; animation: ai-spin 1s linear infinite;"></div>
                    <span style="color: var(--text-muted); font-size: 0.9rem;">Connecting to Gemini to analyze your transcript...</span>
                </div>
                <style>
                    @keyframes ai-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                </style>
            `;
        }

        fetch('/api/student/ai-recommendations')
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    const htmlText = formatMarkdown(res.feedback);
                    content.innerHTML = `<div style="animation: fadeIn 0.3s ease;">${htmlText}</div>`;
                } else {
                    showToast(res.message, 'error');
                    content.innerHTML = `<p style="color: var(--danger); text-align:center; padding:10px 0;">Error generating feedback: ${res.message}</p>`;
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to contact Gemini coach.', 'error');
                content.innerHTML = `<p style="color: var(--danger); text-align:center; padding:10px 0;">Failed to contact AI Coach. Please try again later.</p>`;
            })
            .finally(() => {
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = '💡 Analyze My Performance';
                }
            });
    };

    function formatMarkdown(text) {
        return text
            .split('\n')
            .map(line => {
                line = line.trim();
                if (!line) return '';
                if (line.startsWith('###')) return `<h4 style="margin: 18px 0 8px; font-weight:600; color: var(--primary);">${line.slice(3).trim()}</h4>`;
                if (line.startsWith('##')) return `<h3 style="margin: 22px 0 10px; font-weight:600; color: var(--primary);">${line.slice(2).trim()}</h3>`;
                if (line.startsWith('#')) return `<h2 style="margin: 26px 0 12px; font-weight:700; color: var(--primary);">${line.slice(1).trim()}</h2>`;
                
                if (line.startsWith('*') || line.startsWith('-')) {
                    let cleaned = line.slice(1).trim();
                    cleaned = cleaned.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                    return `<li style="margin-left: 20px; margin-bottom: 6px; list-style-type: disc;">${cleaned}</li>`;
                }
                
                if (/^\d+\./.test(line)) {
                    let cleaned = line.replace(/^\d+\./, '').trim();
                    cleaned = cleaned.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                    return `<li style="margin-left: 20px; margin-bottom: 6px; list-style-type: decimal;">${cleaned}</li>`;
                }
                
                let parsed = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                return `<p style="margin-bottom: 10px;">${parsed}</p>`;
            })
            .filter(x => x !== '')
            .join('');
    }

    // Default Load Performance on startup
    loadPerformanceData();
    checkAttendanceWarning();
    loadStudentNotices();
});
