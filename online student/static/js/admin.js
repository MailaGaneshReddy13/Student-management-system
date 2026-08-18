document.addEventListener('DOMContentLoaded', () => {
    // State management
    let studentsData = [];
    let currentStudentIdForMarks = null;
    let currentStudentIdForAttendance = null;
    let statsChart1 = null;
    let statsChart2 = null;

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
            if (targetSection === 'sec-dashboard') {
                loadDashboardStats();
            } else if (targetSection === 'sec-students') {
                loadStudentsList();
            } else if (targetSection === 'sec-reports') {
                populateReportsDropdown();
            } else if (targetSection === 'sec-notices') {
                loadAnnouncements();
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
    // Section: Dashboard Statistics & Chart.js Rendering
    // ----------------------------------------------------
    function loadDashboardStats() {
        fetch('/api/admin/stats')
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    const data = res.data;
                    document.getElementById('stat-total-students').innerText = data.total_students;
                    document.getElementById('stat-avg-marks').innerText = data.average_marks + '%';
                    document.getElementById('stat-avg-attendance').innerText = data.average_attendance + '%';
                    document.getElementById('stat-pass-rate').innerText = 
                        (data.pass_count + data.fail_count) > 0 
                            ? Math.round((data.pass_count / (data.pass_count + data.fail_count)) * 100) + '%'
                            : 'N/A';

                    renderCharts(data);
                    loadAtRiskStudents(); // Load list of at-risk students
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to load statistics.', 'error');
            });
    }

    function renderCharts(data) {
        // Destroy old instances if they exist
        if (statsChart1) statsChart1.destroy();
        if (statsChart2) statsChart2.destroy();

        const ctx1 = document.getElementById('chart-pass-fail').getContext('2d');
        const ctx2 = document.getElementById('chart-performance').getContext('2d');

        // Pass/Fail distribution chart
        statsChart1 = new Chart(ctx1, {
            type: 'doughnut',
            data: {
                labels: ['Pass (>=40%)', 'Fail (<40%)'],
                datasets: [{
                    data: [data.pass_count, data.fail_count],
                    backgroundColor: ['#10b981', '#f43f5e'],
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

        // Query students list to build department averages representation
        fetch('/api/admin/students')
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    const students = res.data;
                    const deptStats = {};

                    // Group student percentages by department
                    const promises = students.map(s => {
                        return fetch(`/api/admin/students/${s.student_id}/marks`)
                            .then(r => r.json())
                            .then(marksRes => {
                                if (marksRes.success && marksRes.data.total_max > 0) {
                                    const dept = s.department;
                                    if (!deptStats[dept]) deptStats[dept] = [];
                                    deptStats[dept].push(marksRes.data.percentage);
                                }
                            });
                    });

                    Promise.all(promises).then(() => {
                        const labels = Object.keys(deptStats);
                        const averages = labels.map(dept => {
                            const scores = deptStats[dept];
                            return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
                        });

                        // Fallback data if none exist
                        const chartLabels = labels.length ? labels : ['No Dept Data'];
                        const chartData = averages.length ? averages : [0];

                        statsChart2 = new Chart(ctx2, {
                            type: 'bar',
                            data: {
                                labels: chartLabels,
                                datasets: [{
                                    label: 'Average Performance %',
                                    data: chartData,
                                    backgroundColor: 'rgba(99, 102, 241, 0.65)',
                                    borderColor: '#6366f1',
                                    borderWidth: 1.5,
                                    borderRadius: 6
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                scales: {
                                    y: {
                                        min: 0,
                                        max: 100,
                                        ticks: { color: '#94a3b8' },
                                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                                    },
                                    x: {
                                        ticks: { color: '#94a3b8' },
                                        grid: { display: false }
                                    }
                                },
                                plugins: {
                                    legend: { display: false }
                                }
                            }
                        });
                    });
                }
            });
    }

    // ----------------------------------------------------
    // Section: Student Management (CRUD)
    // ----------------------------------------------------
    const studentsTableBody = document.querySelector('#students-table tbody');
    const searchInput = document.getElementById('search-student');
    const filterDept = document.getElementById('filter-dept');
    const filterYear = document.getElementById('filter-year');

    // Trigger filters on input change
    if (searchInput) searchInput.addEventListener('input', debounce(loadStudentsList, 300));
    if (filterDept) filterDept.addEventListener('change', loadStudentsList);
    if (filterYear) filterYear.addEventListener('change', loadStudentsList);

    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    function loadStudentsList() {
        const query = searchInput ? searchInput.value.trim() : '';
        const dept = filterDept ? filterDept.value : '';
        const year = filterYear ? filterYear.value : '';

        let url = '/api/admin/students';
        const params = [];
        if (query) params.push(`search=${encodeURIComponent(query)}`);
        if (dept) params.push(`department=${encodeURIComponent(dept)}`);
        if (year) params.push(`year=${encodeURIComponent(year)}`);
        
        if (params.length) {
            url += `?${params.join('&')}`;
        }

        fetch(url)
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    studentsData = res.data;
                    renderStudentsTable(studentsData);
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to retrieve students list.', 'error');
            });
    }

    function renderStudentsTable(students) {
        studentsTableBody.innerHTML = '';
        if (students.length === 0) {
            studentsTableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No students found matching current criteria.</td></tr>`;
            return;
        }

        students.forEach(student => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${student.student_id}</strong></td>
                <td>${student.name}</td>
                <td>${student.email}</td>
                <td>${student.department}</td>
                <td>${student.year}</td>
                <td>${student.phone || '—'}</td>
                <td>
                    <button class="action-btn edit" onclick="openEditStudentModal('${student.student_id}')" title="Edit Profile">✏️</button>
                    <button class="action-btn marks" onclick="openMarksModal('${student.student_id}')" title="Subject Marks">📊</button>
                    <button class="action-btn attendance" onclick="openAttendanceModal('${student.student_id}')" title="Attendance Records">📅</button>
                    <button class="action-btn delete" onclick="confirmDeleteStudent('${student.student_id}')" title="Delete Student">🗑️</button>
                </td>
            `;
            studentsTableBody.appendChild(tr);
        });
    }

    // Add Student Submit Handler
    const addStudentForm = document.getElementById('add-student-form');
    if (addStudentForm) {
        addStudentForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const student_id = document.getElementById('add-student-id').value.trim();
            const name = document.getElementById('add-student-name').value.trim();
            const email = document.getElementById('add-student-email').value.trim();
            const phone = document.getElementById('add-student-phone').value.trim();
            const department = document.getElementById('add-student-dept').value;
            const year = document.getElementById('add-student-year').value;
            const dob = document.getElementById('add-student-dob').value;
            const password = document.getElementById('add-student-password').value;

            if (!student_id || !name || !email || !department || !year) {
                showToast('Please complete all required fields.', 'warning');
                return;
            }

            fetch('/api/admin/students', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ student_id, name, email, phone, department, year, dob, password })
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast(res.message, 'success');
                    addStudentForm.reset();
                    closeModal('modal-add-student');
                    loadStudentsList();
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to add student.', 'error');
            });
        });
    }

    // Switch Tabs in Unified Management Modal
    window.switchMgmtTab = (tabName) => {
        document.querySelectorAll('.mgmt-tab').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`tab-btn-${tabName}`).classList.add('active');

        document.querySelectorAll('.mgmt-tab-content').forEach(content => content.style.display = 'none');
        document.getElementById(`mgmt-tab-${tabName}`).style.display = 'block';

        const studentId = document.getElementById('mgmt-student-id').value;
        if (studentId) {
            if (tabName === 'marks') {
                loadStudentMarksInModalUnified();
            } else if (tabName === 'attendance') {
                // Default attendance date to today
                document.getElementById('mgmt-att-date').value = new Date().toISOString().split('T')[0];
                loadStudentAttendanceInModalUnified();
            }
        }
    };

    // Helper to open the Unified Student Record Modal
    function initMgmtModal(studentId, defaultTab = 'profile') {
        fetch(`/api/admin/students/${studentId}`)
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    const student = res.data;
                    document.getElementById('mgmt-student-id').value = student.student_id;
                    document.getElementById('mgmt-name').value = student.name;
                    document.getElementById('mgmt-email').value = student.email;
                    document.getElementById('mgmt-phone').value = student.phone || '';
                    document.getElementById('mgmt-dept').value = student.department;
                    document.getElementById('mgmt-year').value = student.year;
                    document.getElementById('mgmt-dob').value = student.dob || '';

                    document.getElementById('mgmt-student-title').innerText = `Manage Student: ${student.name}`;
                    document.getElementById('mgmt-student-subtitle').innerText = `ID: ${student.student_id} | Dept: ${student.department} | ${student.year}`;

                    switchMgmtTab(defaultTab);
                    openModal('modal-student-record');
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to load student details.', 'error');
            });
    }

    // Unified Edit Student / Profile Action
    window.openEditStudentModal = (studentId) => {
        initMgmtModal(studentId, 'profile');
    };

    const mgmtEditForm = document.getElementById('mgmt-edit-form');
    if (mgmtEditForm) {
        mgmtEditForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const studentId = document.getElementById('mgmt-student-id').value;
            const name = document.getElementById('mgmt-name').value.trim();
            const email = document.getElementById('mgmt-email').value.trim();
            const phone = document.getElementById('mgmt-phone').value.trim();
            const department = document.getElementById('mgmt-dept').value;
            const year = document.getElementById('mgmt-year').value;
            const dob = document.getElementById('mgmt-dob').value;

            fetch(`/api/admin/students/${studentId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, phone, department, year, dob })
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast(res.message, 'success');
                    closeModal('modal-student-record');
                    loadStudentsList();
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to update student.', 'error');
            });
        });
    }

    // Delete Student Logic
    window.confirmDeleteStudent = (studentId) => {
        if (confirm(`Are you absolutely sure you want to delete student ${studentId}? All marks and attendance will be permanently lost.`)) {
            fetch(`/api/admin/students/${studentId}`, {
                method: 'DELETE'
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast(res.message, 'success');
                    loadStudentsList();
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to delete student.', 'error');
            });
        }
    };

    // Unified Marks Action
    window.openMarksModal = (studentId) => {
        initMgmtModal(studentId, 'marks');
    };

    function loadStudentMarksInModalUnified() {
        const studentId = document.getElementById('mgmt-student-id').value;
        if (!studentId) return;
        
        fetch(`/api/admin/students/${studentId}/marks`)
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    const data = res.data;
                    const tbody = document.querySelector('#mgmt-marks-table tbody');
                    tbody.innerHTML = '';
                    
                    if (data.subjects.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No marks logged.</td></tr>`;
                        document.getElementById('mgmt-marks-summary').innerHTML = 'Total: 0 | Average: 0% | Grade: N/A';
                        return;
                    }

                    data.subjects.forEach(subject => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${subject.subject_name}</td>
                            <td><strong>${subject.marks_obtained}</strong></td>
                            <td>${subject.max_marks}</td>
                            <td><span class="badge grade-${subject.grade.replace('+', '-plus')}">${subject.grade}</span></td>
                            <td>
                                <button class="action-btn delete" onclick="deleteSubjectMarksUnified('${subject.subject_name}')">🗑️</button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });

                    document.getElementById('mgmt-marks-summary').innerHTML = 
                        `Total Obtained: <strong>${data.total_obtained}</strong>/${data.total_max} &nbsp;|&nbsp; ` +
                        `Percentage: <strong>${data.percentage}%</strong> &nbsp;|&nbsp; ` +
                        `Grade: <span class="badge badge-grade grade-${data.grade.replace('+', '-plus')}">${data.grade}</span>`;
                }
            });
    }

    const mgmtMarksForm = document.getElementById('mgmt-marks-form');
    if (mgmtMarksForm) {
        mgmtMarksForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const studentId = document.getElementById('mgmt-student-id').value;
            const subject_name = document.getElementById('mgmt-mark-subject').value.trim();
            const marks_obtained = document.getElementById('mgmt-mark-obtained').value.trim();
            const max_marks = document.getElementById('mgmt-mark-max').value.trim() || 100;

            if (!subject_name || marks_obtained === '') {
                showToast('Please fill subject name and marks obtained.', 'warning');
                return;
            }

            fetch(`/api/admin/students/${studentId}/marks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ subject_name, marks_obtained, max_marks })
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast(res.message, 'success');
                    mgmtMarksForm.reset();
                    loadStudentMarksInModalUnified();
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to add marks.', 'error');
            });
        });
    }

    window.deleteSubjectMarksUnified = (subjectName) => {
        const studentId = document.getElementById('mgmt-student-id').value;
        if (confirm(`Remove marks for subject "${subjectName}"?`)) {
            fetch(`/api/admin/students/${studentId}/marks/${encodeURIComponent(subjectName)}`, {
                method: 'DELETE'
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast(res.message, 'success');
                    loadStudentMarksInModalUnified();
                } else {
                    showToast(res.message, 'error');
                }
            });
        }
    };

    // Unified Attendance Action
    window.openAttendanceModal = (studentId) => {
        initMgmtModal(studentId, 'attendance');
    };

    function loadStudentAttendanceInModalUnified() {
        const studentId = document.getElementById('mgmt-student-id').value;
        if (!studentId) return;

        fetch(`/api/admin/students/${studentId}/attendance`)
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    const data = res.data;
                    const tbody = document.querySelector('#mgmt-att-table tbody');
                    tbody.innerHTML = '';
                    
                    if (data.logs.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="2" style="text-align: center; color: var(--text-muted);">No attendance logged.</td></tr>`;
                        document.getElementById('mgmt-att-summary').innerHTML = 'No Records. Attendance: 100%';
                        return;
                    }

                    data.logs.forEach(log => {
                        const tr = document.createElement('tr');
                        const statusClass = log.status.toLowerCase();
                        tr.innerHTML = `
                            <td>${log.date}</td>
                            <td><span class="badge badge-${statusClass}">${log.status}</span></td>
                        `;
                        tbody.appendChild(tr);
                    });

                    document.getElementById('mgmt-att-summary').innerHTML = 
                        `Total Days Checked: <strong>${data.summary.total}</strong> &nbsp;|&nbsp; ` +
                        `P: ${data.summary.counts.Present} &nbsp;&bull;&nbsp; ` +
                        `A: ${data.summary.counts.Absent} &nbsp;&bull;&nbsp; ` +
                        `L: ${data.summary.counts.Late} &nbsp;|&nbsp; ` +
                        `Overall Attendance: <strong>${data.summary.rate}%</strong>`;
                }
            });
    }

    const mgmtAttForm = document.getElementById('mgmt-att-form');
    if (mgmtAttForm) {
        mgmtAttForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const studentId = document.getElementById('mgmt-student-id').value;
            const date = document.getElementById('mgmt-att-date').value;
            const status = document.getElementById('mgmt-att-status').value;

            if (!date || !status) {
                showToast('Please select a date and status.', 'warning');
                return;
            }

            fetch(`/api/admin/students/${studentId}/attendance`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date, status })
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast(res.message, 'success');
                    loadStudentAttendanceInModalUnified();
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to add attendance record.', 'error');
            });
        });
    }

    // ----------------------------------------------------
    // Section: Performance Reports & Printing
    // ----------------------------------------------------
    const reportStudentSelect = document.getElementById('report-student-select');
    const reportCardContainer = document.getElementById('report-card-container');

    function populateReportsDropdown() {
        fetch('/api/admin/students')
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    reportStudentSelect.innerHTML = `<option value="">-- Choose a Student --</option>`;
                    res.data.forEach(s => {
                        const opt = document.createElement('option');
                        opt.value = s.student_id;
                        opt.innerText = `${s.name} (${s.student_id}) - ${s.department}`;
                        reportStudentSelect.appendChild(opt);
                    });
                }
            });
    }

    if (reportStudentSelect) {
        reportStudentSelect.addEventListener('change', () => {
            const sid = reportStudentSelect.value;
            if (!sid) {
                reportCardContainer.style.display = 'none';
                return;
            }

            // Fetch profile, marks, and attendance to build the ultimate performance card
            Promise.all([
                fetch(`/api/admin/students/${sid}`).then(r => r.json()),
                fetch(`/api/admin/students/${sid}/marks`).then(r => r.json()),
                fetch(`/api/admin/students/${sid}/attendance`).then(r => r.json())
            ]).then(([profileRes, marksRes, attRes]) => {
                if (profileRes.success && marksRes.success && attRes.success) {
                    const student = profileRes.data;
                    const marks = marksRes.data;
                    const att = attRes.data;

                    reportCardContainer.style.display = 'block';
                    document.getElementById('rep-student-name').innerText = student.name;
                    document.getElementById('rep-student-id').innerText = student.student_id;
                    document.getElementById('rep-student-dept').innerText = student.department;
                    document.getElementById('rep-student-year').innerText = student.year;
                    document.getElementById('rep-student-email').innerText = student.email;
                    document.getElementById('rep-student-phone').innerText = student.phone || '—';
                    document.getElementById('rep-student-dob').innerText = student.dob || '—';

                    // Marks Details Table
                    const marksTbody = document.getElementById('rep-marks-tbody');
                    marksTbody.innerHTML = '';
                    if (marks.subjects.length === 0) {
                        marksTbody.innerHTML = `<tr><td colspan="4" style="text-align: center;">No subject scores recorded yet.</td></tr>`;
                    } else {
                        marks.subjects.forEach(sub => {
                            const pct = Math.round(sub.marks_obtained / sub.max_marks * 100);
                            const grade = calculateGradeOffline(pct);
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td>${sub.subject_name}</td>
                                <td>${sub.marks_obtained}</td>
                                <td>${sub.max_marks}</td>
                                <td><span class="badge grade-${grade.replace('+', '-plus')}">${grade}</span></td>
                            `;
                            marksTbody.appendChild(tr);
                        });
                    }

                    // Totals
                    document.getElementById('rep-marks-obtained').innerText = marks.total_obtained;
                    document.getElementById('rep-marks-max').innerText = marks.total_max;
                    document.getElementById('rep-percentage').innerText = marks.percentage + '%';
                    document.getElementById('rep-grade').innerText = marks.grade;
                    document.getElementById('rep-grade').className = `badge badge-grade grade-${marks.grade.replace('+', '-plus')}`;

                    // Attendance Details
                    document.getElementById('rep-att-rate').innerText = att.summary.rate + '%';
                    document.getElementById('rep-att-details').innerText = 
                        `Total Sessions: ${att.summary.total} | Present: ${att.summary.counts.Present} | Absent: ${att.summary.counts.Absent} | Late: ${att.summary.counts.Late}`;
                }
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

    window.printReport = () => {
        window.print();
    };

    // ----------------------------------------------------
    // Section: Backup & File Upload Handlers (File Handling)
    // ----------------------------------------------------
    const importJsonForm = document.getElementById('import-json-form');
    if (importJsonForm) {
        importJsonForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('import-json-file');
            if (fileInput.files.length === 0) {
                showToast('Please select a JSON backup file.', 'warning');
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            fetch('/api/admin/backup/import/json', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast(res.message, 'success');
                    importJsonForm.reset();
                    loadDashboardStats(); // Refresh dashboard numbers
                    
                    // Display errors if any entries failed
                    if (res.data.errors.length > 0) {
                        alert("Some entries failed during import:\n" + res.data.errors.join("\n"));
                    }
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to import JSON file.', 'error');
            });
        });
    }

    const importCsvForm = document.getElementById('import-csv-form');
    if (importCsvForm) {
        importCsvForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('import-csv-file');
            if (fileInput.files.length === 0) {
                showToast('Please select a CSV file.', 'warning');
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            fetch('/api/admin/backup/import/csv', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast(res.message, 'success');
                    importCsvForm.reset();
                    loadDashboardStats();
                    
                    if (res.data.errors.length > 0) {
                        alert("Some entries failed during import:\n" + res.data.errors.join("\n"));
                    }
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to import CSV file.', 'error');
            });
        });
    }

    // ----------------------------------------------------
    // Section: Notices Noticeboard and At-Risk list helpers
    // ----------------------------------------------------
    const atRiskTableBody = document.querySelector('#at-risk-table tbody');

    function loadAtRiskStudents() {
        if (!atRiskTableBody) return;
        fetch('/api/admin/attendance/at-risk?threshold=75.0')
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    atRiskTableBody.innerHTML = '';
                    const list = res.data;
                    if (list.length === 0) {
                        atRiskTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--success);">All students are above the 75% attendance threshold.</td></tr>`;
                        return;
                    }
                    list.forEach(student => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td><strong>${student.student_id}</strong></td>
                            <td>${student.name}</td>
                            <td>${student.department}</td>
                            <td>${student.year}</td>
                            <td><span class="badge badge-absent">${student.rate}%</span></td>
                            <td>${student.total_days}</td>
                        `;
                        atRiskTableBody.appendChild(tr);
                    });
                }
            });
    }

    const adminNoticeList = document.getElementById('admin-notice-list');

    function loadAnnouncements() {
        if (!adminNoticeList) return;
        fetch('/api/announcements')
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    adminNoticeList.innerHTML = '';
                    const list = res.data;
                    if (list.length === 0) {
                        adminNoticeList.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">No announcements posted yet.</div>`;
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
                            <button class="action-btn delete" onclick="deleteNotice(${notice.id})" style="position: absolute; top: 15px; right: 15px;" title="Delete Announcement">🗑️</button>
                        `;
                        adminNoticeList.appendChild(div);
                    });
                }
            });
    }

    const createNoticeForm = document.getElementById('create-notice-form');
    if (createNoticeForm) {
        createNoticeForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const title = document.getElementById('notice-title').value.trim();
            const content = document.getElementById('notice-content').value.trim();

            fetch('/api/admin/announcements', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, content })
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast(res.message, 'success');
                    createNoticeForm.reset();
                    loadAnnouncements();
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to publish announcement.', 'error');
            });
        });
    }

    window.deleteNotice = (noticeId) => {
        if (confirm('Delete this announcement bulletin permanently?')) {
            fetch(`/api/admin/announcements/${noticeId}`, {
                method: 'DELETE'
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast(res.message, 'success');
                    loadAnnouncements();
                } else {
                    showToast(res.message, 'error');
                }
            });
        }
    };

    // ----------------------------------------------------
    // Section: Demo Data Seeder
    // ----------------------------------------------------
    window.seedDemoData = () => {
        const btn = document.getElementById('btn-seed-data');
        const result = document.getElementById('seed-result');
        if (btn) {
            btn.disabled = true;
            btn.textContent = '⏳ Seeding...';
        }
        fetch('/api/admin/seed-data', { method: 'POST' })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    showToast(res.message, 'success');
                    if (result) {
                        result.style.display = 'block';
                        result.textContent = `✓ ${res.message} (Created: ${res.data.created.join(', ') || 'none'})`;
                    }
                    loadDashboardStats();
                    // Auto-navigate to Students section after seeding
                    setTimeout(() => {
                        const studentsLink = document.querySelector('[data-target="sec-students"]');
                        if (studentsLink) studentsLink.click();
                    }, 1200);
                } else {
                    showToast(res.message, 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to seed demo data.', 'error');
            })
            .finally(() => {
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = '⚡ Seed Sample Students';
                }
            });
    };

    // ----------------------------------------------------
    // Section: Gemini AI Assistant Handlers
    // ----------------------------------------------------
    let rawAIExtractedText = '';

    window.prefillAIPrompt = (type) => {
        const input = document.getElementById('ai-prompt-input');
        if (!input) return;
        
        if (type === 'announcement') {
            input.value = "Draft a formal notice board announcement about the upcoming mid-semester examinations. Specify that student ID cards are mandatory and calculators are allowed only for engineering departments.";
        } else if (type === 'warning') {
            input.value = "Write a gentle but firm email notice warning students whose attendance has fallen below 75%. Remind them that attendance is critical for hall ticket release and encourage them to consult their department heads.";
        }
    };

    const aiPromptForm = document.getElementById('ai-prompt-form');
    if (aiPromptForm) {
        aiPromptForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const prompt = document.getElementById('ai-prompt-input').value.trim();
            const outputContainer = document.getElementById('ai-output-container');
            const actionButtons = document.getElementById('ai-action-buttons');
            const submitBtn = document.getElementById('btn-submit-ai-prompt');

            if (!prompt) return;

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = '🤖 Thinking...';
            }
            if (outputContainer) {
                outputContainer.innerHTML = `
                    <div style="display:flex; flex-direction:column; align-items:center; gap:12px; padding: 70px 0;">
                        <div style="border: 3px solid rgba(255,255,255,0.1); border-top: 3px solid var(--primary); border-radius: 50%; width: 28px; height: 28px; animation: ai-spin 1s linear infinite;"></div>
                        <span style="color: var(--text-muted); font-size: 0.9rem;">Gemini is drafting your response...</span>
                    </div>
                    <style>
                        @keyframes ai-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                    </style>
                `;
            }
            if (actionButtons) actionButtons.style.display = 'none';

            fetch('/api/admin/ai-assistant', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    rawAIExtractedText = res.response;
                    const htmlText = formatAIResponse(res.response);
                    outputContainer.innerHTML = `<div style="animation: fadeIn 0.3s ease;">${htmlText}</div>`;
                    if (actionButtons) actionButtons.style.display = 'flex';
                } else {
                    showToast(res.message, 'error');
                    outputContainer.innerHTML = `<p style="color: var(--danger); text-align:center; padding:50px 0;">Error: ${res.message}</p>`;
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Failed to connect to Gemini API.', 'error');
                outputContainer.innerHTML = `<p style="color: var(--danger); text-align:center; padding:50px 0;">Connection failed. Check your API key.</p>`;
            })
            .finally(() => {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = '⚡ Ask Gemini';
                }
            });
        });
    }

    window.copyAIOutput = () => {
        if (!rawAIExtractedText) return;
        navigator.clipboard.writeText(rawAIExtractedText)
            .then(() => showToast('Copied to clipboard!', 'success'))
            .catch(err => console.error('Copy failed:', err));
    };

    window.useAIOutputAsNotice = () => {
        if (!rawAIExtractedText) return;
        
        // Strip markdown headings or extract a title
        let lines = rawAIExtractedText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        let title = "AI Generated Notice";
        let content = rawAIExtractedText;

        if (lines.length > 0) {
            // If the first line is a title/heading, extract it
            if (lines[0].startsWith('#') || lines[0].startsWith('Title:') || lines[0].startsWith('Subject:')) {
                title = lines[0].replace(/^[#\s]+|^(Title:|Subject:)\s*/gi, '');
                content = lines.slice(1).join('\n');
            } else if (lines[0].length < 60) {
                title = lines[0];
                content = lines.slice(1).join('\n');
            }
        }

        // Navigate to Noticeboard tab
        const noticeTabBtn = document.querySelector('[data-target="sec-notices"]');
        if (noticeTabBtn) {
            noticeTabBtn.click();
            // Prefill notices form
            document.getElementById('notice-title').value = title;
            document.getElementById('notice-content').value = content.trim();
            showToast('Draft transferred to Noticeboard! Click "Publish Bulletin" to publish.', 'info');
        }
    };

    function formatAIResponse(text) {
        return text
            .split('\n')
            .map(line => {
                line = line.trim();
                if (!line) return '';
                if (line.startsWith('###')) return `<h4 style="margin: 14px 0 6px; font-weight:600; color: var(--primary);">${line.slice(3).trim()}</h4>`;
                if (line.startsWith('##')) return `<h3 style="margin: 16px 0 8px; font-weight:600; color: var(--primary);">${line.slice(2).trim()}</h3>`;
                if (line.startsWith('#')) return `<h2 style="margin: 20px 0 10px; font-weight:700; color: var(--primary);">${line.slice(1).trim()}</h2>`;
                
                if (line.startsWith('*') || line.startsWith('-')) {
                    let cleaned = line.slice(1).trim();
                    cleaned = cleaned.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                    return `<li style="margin-left: 15px; margin-bottom: 4px; list-style-type: disc;">${cleaned}</li>`;
                }
                
                let parsed = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                return `<p style="margin-bottom: 8px;">${parsed}</p>`;
            })
            .filter(x => x !== '')
            .join('');
    }

    // Initialize Dashboard Stats on load
    loadDashboardStats();
});
