// 智能教案生成平台前端应用
class LessonPlannerApp {
    constructor() {
        this.currentSection = 'dashboard';
        this.websocket = null;
        this.user = null;
        this.notifications = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupNavigation();
        this.loadDashboard();
        this.connectWebSocket();
        this.checkAuth();
    }

    setupEventListeners() {
        // 侧边栏切换
        document.getElementById('sidebar-toggle').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });

        document.getElementById('sidebar-close').addEventListener('click', () => {
            document.getElementById('sidebar').classList.remove('open');
        });

        // 用户菜单
        document.getElementById('user-menu-btn').addEventListener('click', () => {
            document.getElementById('user-menu').classList.toggle('hidden');
        });

        // 点击外部关闭用户菜单
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#user-menu-btn')) {
                document.getElementById('user-menu').classList.add('hidden');
            }
        });

        // 退出登录
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.logout();
        });

        // 文件上传
        document.getElementById('select-files-btn').addEventListener('click', () => {
            document.getElementById('file-input').click();
        });

        document.getElementById('file-input').addEventListener('change', (e) => {
            this.handleFileUpload(e.target.files);
        });

        // 拖拽上传
        const uploadArea = document.getElementById('upload-area');
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('border-blue-500', 'bg-blue-50');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('border-blue-500', 'bg-blue-50');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('border-blue-500', 'bg-blue-50');
            this.handleFileUpload(e.dataTransfer.files);
        });

        // 搜索功能
        document.getElementById('document-search-btn').addEventListener('click', () => {
            this.searchDocuments();
        });

        document.getElementById('lesson-plan-search-btn').addEventListener('click', () => {
            this.searchLessonPlans();
        });

        document.getElementById('advanced-search-btn').addEventListener('click', () => {
            this.advancedSearch();
        });

        // 导出功能
        document.getElementById('export-documents-btn-page').addEventListener('click', () => {
            this.exportDocuments();
        });

        document.getElementById('export-lesson-plans-btn-page').addEventListener('click', () => {
            this.exportLessonPlans();
        });

        document.getElementById('export-all-data-btn').addEventListener('click', () => {
            this.exportAllData();
        });

        document.getElementById('export-stats-btn').addEventListener('click', () => {
            this.exportStats();
        });

        // 设置保存
        document.getElementById('save-settings-btn').addEventListener('click', () => {
            this.saveSettings();
        });
    }

    setupNavigation() {
        // 侧边栏链接
        document.querySelectorAll('.sidebar-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = e.target.closest('a').getAttribute('href').substring(1);
                this.showSection(section);
            });
        });

        // 顶部导航链接
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = e.target.getAttribute('href').substring(1);
                this.showSection(section);
            });
        });
    }

    showSection(sectionName) {
        // 隐藏所有section
        document.querySelectorAll('.section').forEach(section => {
            section.classList.add('hidden');
        });

        // 显示目标section
        const targetSection = document.getElementById(sectionName);
        if (targetSection) {
            targetSection.classList.remove('hidden');
            this.currentSection = sectionName;
        }

        // 更新导航状态
        this.updateNavigationState(sectionName);

        // 加载对应数据
        this.loadSectionData(sectionName);
    }

    updateNavigationState(activeSection) {
        // 更新侧边栏链接状态
        document.querySelectorAll('.sidebar-link').forEach(link => {
            link.classList.remove('bg-blue-100', 'text-blue-700');
            if (link.getAttribute('href') === `#${activeSection}`) {
                link.classList.add('bg-blue-100', 'text-blue-700');
            }
        });

        // 更新顶部导航状态
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('bg-white', 'bg-opacity-10');
            if (link.getAttribute('href') === `#${activeSection}`) {
                link.classList.add('bg-white', 'bg-opacity-10');
            }
        });
    }

    loadSectionData(sectionName) {
        switch (sectionName) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'documents':
                this.loadDocuments();
                break;
            case 'lesson-plans':
                this.loadLessonPlans();
                break;
            case 'upload':
                this.loadUploadSection();
                break;
            case 'export':
                this.loadExportSection();
                break;
            case 'search':
                this.loadSearchSection();
                break;
            case 'settings':
                this.loadSettings();
                break;
        }
    }

    async loadDashboard() {
        try {
            // 加载统计数据
            const stats = await this.fetchStats();
            this.updateDashboardStats(stats);

            // 加载最近活动
            const recentDocs = await this.fetchRecentDocuments();
            const recentPlans = await this.fetchRecentLessonPlans();
            this.updateRecentActivities(recentDocs, recentPlans);

        } catch (error) {
            console.error('加载仪表板失败:', error);
            this.showNotification('加载仪表板失败', 'error');
        }
    }

    updateDashboardStats(stats) {
        document.getElementById('total-documents').textContent = stats.total_documents || 0;
        document.getElementById('total-lesson-plans').textContent = stats.total_lesson_plans || 0;
        document.getElementById('today-uploads').textContent = stats.today_uploads || 0;
        document.getElementById('today-exports').textContent = stats.today_exports || 0;
    }

    updateRecentActivities(documents, lessonPlans) {
        // 更新最近文档
        const recentDocsContainer = document.getElementById('recent-documents');
        if (documents && documents.length > 0) {
            recentDocsContainer.innerHTML = documents.slice(0, 5).map(doc => `
                <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div class="flex items-center">
                        <i class="fas fa-file-alt text-blue-500 mr-3"></i>
                        <div>
                            <p class="font-medium text-gray-900">${doc.title}</p>
                            <p class="text-sm text-gray-500">${doc.file_type} • ${this.formatFileSize(doc.file_size)}</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-400">${this.formatDate(doc.created_at)}</span>
                </div>
            `).join('');
        } else {
            recentDocsContainer.innerHTML = '<div class="text-gray-500 text-center py-4">暂无数据</div>';
        }

        // 更新最近教案
        const recentPlansContainer = document.getElementById('recent-lesson-plans');
        if (lessonPlans && lessonPlans.length > 0) {
            recentPlansContainer.innerHTML = lessonPlans.slice(0, 5).map(plan => `
                <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div class="flex items-center">
                        <i class="fas fa-book text-green-500 mr-3"></i>
                        <div>
                            <p class="font-medium text-gray-900">${plan.title}</p>
                            <p class="text-sm text-gray-500">${plan.subject} • ${plan.grade_level}</p>
                        </div>
                    </div>
                    <span class="text-xs text-gray-400">${this.formatDate(plan.created_at)}</span>
                </div>
            `).join('');
        } else {
            recentPlansContainer.innerHTML = '<div class="text-gray-500 text-center py-4">暂无数据</div>';
        }
    }

    async loadDocuments() {
        try {
            const documents = await this.fetchDocuments();
            this.renderDocumentsList(documents);
        } catch (error) {
            console.error('加载文档失败:', error);
            this.showNotification('加载文档失败', 'error');
        }
    }

    async loadLessonPlans() {
        try {
            const lessonPlans = await this.fetchLessonPlans();
            this.renderLessonPlansList(lessonPlans);
        } catch (error) {
            console.error('加载教案失败:', error);
            this.showNotification('加载教案失败', 'error');
        }
    }

    renderDocumentsList(documents) {
        const container = document.getElementById('documents-list');
        if (documents && documents.length > 0) {
            container.innerHTML = documents.map(doc => `
                <div class="px-6 py-4 hover:bg-gray-50">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <input type="checkbox" class="document-checkbox mr-3" value="${doc.id}">
                            <i class="fas fa-file-alt text-blue-500 mr-3"></i>
                            <div>
                                <h4 class="font-medium text-gray-900">${doc.title}</h4>
                                <p class="text-sm text-gray-500">${doc.description || '无描述'}</p>
                                <div class="flex items-center mt-1 space-x-2">
                                    <span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">${doc.file_type}</span>
                                    <span class="text-xs text-gray-500">${this.formatFileSize(doc.file_size)}</span>
                                    <span class="text-xs text-gray-500">${this.formatDate(doc.created_at)}</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex space-x-2">
                            <button onclick="app.downloadDocument(${doc.id})" class="text-blue-600 hover:text-blue-800 px-2 py-1 rounded">
                                <i class="fas fa-download"></i>
                            </button>
                            <button onclick="app.editDocument(${doc.id})" class="text-green-600 hover:text-green-800 px-2 py-1 rounded">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button onclick="app.deleteDocument(${doc.id})" class="text-red-600 hover:text-red-800 px-2 py-1 rounded">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="text-gray-500 text-center py-8">暂无文档</div>';
        }
    }

    renderLessonPlansList(lessonPlans) {
        const container = document.getElementById('lesson-plans-list');
        if (lessonPlans && lessonPlans.length > 0) {
            container.innerHTML = lessonPlans.map(plan => `
                <div class="px-6 py-4 hover:bg-gray-50">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <input type="checkbox" class="lesson-plan-checkbox mr-3" value="${plan.id}">
                            <i class="fas fa-book text-green-500 mr-3"></i>
                            <div>
                                <h4 class="font-medium text-gray-900">${plan.title}</h4>
                                <p class="text-sm text-gray-500">${plan.learning_objectives || '无学习目标'}</p>
                                <div class="flex items-center mt-1 space-x-2">
                                    <span class="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">${plan.subject}</span>
                                    <span class="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">${plan.grade_level}</span>
                                    <span class="text-xs text-gray-500">${plan.duration_minutes}分钟</span>
                                    <span class="text-xs text-gray-500">${this.formatDate(plan.created_at)}</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex space-x-2">
                            <button onclick="app.viewLessonPlan(${plan.id})" class="text-blue-600 hover:text-blue-800 px-2 py-1 rounded">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button onclick="app.editLessonPlan(${plan.id})" class="text-green-600 hover:text-green-800 px-2 py-1 rounded">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button onclick="app.deleteLessonPlan(${plan.id})" class="text-red-600 hover:text-red-800 px-2 py-1 rounded">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="text-gray-500 text-center py-8">暂无教案</div>';
        }
    }

    async handleFileUpload(files) {
        if (!files || files.length === 0) return;

        const uploadProgress = document.getElementById('upload-progress');
        const uploadItems = document.getElementById('upload-items');
        
        uploadProgress.classList.remove('hidden');
        uploadItems.innerHTML = '';

        for (let file of files) {
            const uploadItem = this.createUploadItem(file);
            uploadItems.appendChild(uploadItem);

            try {
                await this.uploadFile(file, uploadItem);
            } catch (error) {
                console.error('文件上传失败:', error);
                this.updateUploadItemStatus(uploadItem, 'failed', error.message);
            }
        }
    }

    createUploadItem(file) {
        const item = document.createElement('div');
        item.className = 'bg-gray-50 rounded-lg p-4';
        item.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <div class="flex items-center">
                    <i class="fas fa-file-alt text-blue-500 mr-2"></i>
                    <span class="font-medium">${file.name}</span>
                </div>
                <span class="text-sm text-gray-500">${this.formatFileSize(file.size)}</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="upload-progress-bar bg-blue-600 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
            </div>
            <div class="flex items-center justify-between mt-2">
                <span class="text-sm text-gray-600">准备上传...</span>
                <span class="upload-percentage text-sm font-medium text-blue-600">0%</span>
            </div>
        `;
        return item;
    }

    updateUploadItemStatus(item, status, message = '') {
        const progressBar = item.querySelector('.upload-progress-bar');
        const statusText = item.querySelector('.text-gray-600');
        const percentage = item.querySelector('.upload-percentage');

        switch (status) {
            case 'uploading':
                progressBar.classList.remove('bg-blue-600', 'bg-green-600', 'bg-red-600');
                progressBar.classList.add('bg-blue-600');
                statusText.textContent = '上传中...';
                break;
            case 'completed':
                progressBar.classList.remove('bg-blue-600', 'bg-red-600');
                progressBar.classList.add('bg-green-600');
                statusText.textContent = '上传完成';
                percentage.textContent = '100%';
                break;
            case 'failed':
                progressBar.classList.remove('bg-blue-600', 'bg-green-600');
                progressBar.classList.add('bg-red-600');
                statusText.textContent = `上传失败: ${message}`;
                break;
        }
    }

    async uploadFile(file, uploadItem) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('title', file.name);
        formData.append('description', `上传的文件: ${file.name}`);

        try {
            const response = await fetch('/api/v1/documents/upload', {
                method: 'POST',
                body: formData,
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (response.ok) {
                this.updateUploadItemStatus(uploadItem, 'completed');
                this.showNotification('文件上传成功', 'success');
                
                // 刷新文档列表
                if (this.currentSection === 'documents') {
                    this.loadDocuments();
                }
            } else {
                const error = await response.json();
                throw new Error(error.detail || '上传失败');
            }
        } catch (error) {
            throw error;
        }
    }

    async searchDocuments() {
        const searchTerm = document.getElementById('document-search').value;
        const fileType = document.getElementById('document-type-filter').value;
        const tags = document.getElementById('document-tags-filter').value;

        try {
            const params = new URLSearchParams();
            if (searchTerm) params.append('search', searchTerm);
            if (fileType) params.append('file_type', fileType);
            if (tags) params.append('tags', tags);

            const response = await fetch(`/api/v1/documents/?${params}`, {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (response.ok) {
                const documents = await response.json();
                this.renderDocumentsList(documents);
            } else {
                throw new Error('搜索失败');
            }
        } catch (error) {
            console.error('搜索文档失败:', error);
            this.showNotification('搜索失败', 'error');
        }
    }

    async searchLessonPlans() {
        const searchTerm = document.getElementById('lesson-plan-search').value;
        const subject = document.getElementById('lesson-plan-subject-filter').value;
        const gradeLevel = document.getElementById('lesson-plan-grade-filter').value;

        try {
            const params = new URLSearchParams();
            if (searchTerm) params.append('search', searchTerm);
            if (subject) params.append('subject', subject);
            if (gradeLevel) params.append('grade_level', gradeLevel);

            const response = await fetch(`/api/v1/lesson-plans/?${params}`, {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (response.ok) {
                const lessonPlans = await response.json();
                this.renderLessonPlansList(lessonPlans);
            } else {
                throw new Error('搜索失败');
            }
        } catch (error) {
            console.error('搜索教案失败:', error);
            this.showNotification('搜索失败', 'error');
        }
    }

    async advancedSearch() {
        const keyword = document.getElementById('advanced-search-keyword').value;
        const type = document.getElementById('advanced-search-type').value;

        if (!keyword.trim()) {
            this.showNotification('请输入搜索关键词', 'warning');
            return;
        }

        try {
            let results = [];
            
            if (type === 'all' || type === 'documents') {
                const docsResponse = await fetch(`/api/v1/documents/?search=${encodeURIComponent(keyword)}`, {
                    headers: {
                        'Authorization': `Bearer ${this.getAuthToken()}`
                    }
                });
                if (docsResponse.ok) {
                    const docs = await docsResponse.json();
                    results.push(...docs.map(doc => ({ ...doc, type: 'document' })));
                }
            }

            if (type === 'all' || type === 'lesson-plans') {
                const plansResponse = await fetch(`/api/v1/lesson-plans/?search=${encodeURIComponent(keyword)}`, {
                    headers: {
                        'Authorization': `Bearer ${this.getAuthToken()}`
                    }
                });
                if (plansResponse.ok) {
                    const plans = await plansResponse.json();
                    results.push(...plans.map(plan => ({ ...plan, type: 'lesson_plan' })));
                }
            }

            this.displaySearchResults(results);
        } catch (error) {
            console.error('高级搜索失败:', error);
            this.showNotification('搜索失败', 'error');
        }
    }

    displaySearchResults(results) {
        const container = document.getElementById('search-results');
        const content = document.getElementById('search-results-content');

        if (results.length > 0) {
            content.innerHTML = results.map(result => `
                <div class="border-b border-gray-200 py-4 last:border-b-0">
                    <div class="flex items-start justify-between">
                        <div class="flex items-start">
                            <i class="fas fa-${result.type === 'document' ? 'file-alt text-blue-500' : 'book text-green-500'} mr-3 mt-1"></i>
                            <div>
                                <h4 class="font-medium text-gray-900">${result.title}</h4>
                                <p class="text-sm text-gray-600 mt-1">${result.type === 'document' ? (result.description || '无描述') : (result.learning_objectives || '无学习目标')}</p>
                                <div class="flex items-center mt-2 space-x-2">
                                    <span class="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">${result.type === 'document' ? '文档' : '教案'}</span>
                                    ${result.type === 'lesson_plan' ? `<span class="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">${result.subject}</span>` : ''}
                                    <span class="text-xs text-gray-500">${this.formatDate(result.created_at)}</span>
                                </div>
                            </div>
                        </div>
                        <button onclick="app.view${result.type === 'document' ? 'Document' : 'LessonPlan'}(${result.id})" class="text-blue-600 hover:text-blue-800 px-3 py-1 rounded border border-blue-300 hover:bg-blue-50">
                            查看
                        </button>
                    </div>
                </div>
            `).join('');
            
            container.classList.remove('hidden');
        } else {
            content.innerHTML = '<div class="text-gray-500 text-center py-8">未找到相关结果</div>';
            container.classList.remove('hidden');
        }
    }

    async exportDocuments() {
        const format = document.getElementById('document-export-format').value;
        await this.exportData('documents', format);
    }

    async exportLessonPlans() {
        const format = document.getElementById('lesson-plan-export-format').value;
        await this.exportData('lesson-plans', format);
    }

    async exportAllData() {
        const format = document.getElementById('all-data-export-format').value;
        await this.exportData('all', format);
    }

    async exportStats() {
        try {
            const response = await fetch('/api/v1/export/stats', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (response.ok) {
                const stats = await response.json();
                this.downloadData(stats, 'stats', 'json');
            } else {
                throw new Error('获取统计信息失败');
            }
        } catch (error) {
            console.error('导出统计失败:', error);
            this.showNotification('导出统计失败', 'error');
        }
    }

    async exportData(type, format) {
        try {
            let url = '';
            switch (type) {
                case 'documents':
                    url = `/api/v1/export/documents?format=${format}`;
                    break;
                case 'lesson-plans':
                    url = `/api/v1/export/lesson-plans?format=${format}`;
                    break;
                case 'all':
                    url = `/api/v1/export/all?format=${format}`;
                    break;
            }

            const response = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (response.ok) {
                const blob = await response.blob();
                this.downloadBlob(blob, `export_${type}_${new Date().toISOString().split('T')[0]}.${format}`);
                this.showNotification('导出成功', 'success');
            } else {
                throw new Error('导出失败');
            }
        } catch (error) {
            console.error('导出失败:', error);
            this.showNotification('导出失败', 'error');
        }
    }

    downloadBlob(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    downloadData(data, filename, format) {
        let content, mimeType, extension;
        
        switch (format) {
            case 'json':
                content = JSON.stringify(data, null, 2);
                mimeType = 'application/json';
                extension = 'json';
                break;
            case 'csv':
                content = this.convertToCSV(data);
                mimeType = 'text/csv';
                extension = 'csv';
                break;
            default:
                content = JSON.stringify(data, null, 2);
                mimeType = 'application/json';
                extension = 'json';
        }

        const blob = new Blob([content], { type: mimeType });
        this.downloadBlob(blob, `${filename}.${extension}`);
    }

    convertToCSV(data) {
        // 简单的CSV转换实现
        if (Array.isArray(data)) {
            if (data.length === 0) return '';
            
            const headers = Object.keys(data[0]);
            const csvRows = [headers.join(',')];
            
            for (const row of data) {
                const values = headers.map(header => {
                    const value = row[header];
                    return typeof value === 'string' ? `"${value.replace(/"/g, '""')}"` : value;
                });
                csvRows.push(values.join(','));
            }
            
            return csvRows.join('\n');
        }
        
        return JSON.stringify(data);
    }

    connectWebSocket() {
        if (!this.user) return;

        const wsUrl = `ws://localhost:6783/api/v1/ws/${this.user.id}`;
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            this.updateWebSocketStatus('connected', '已连接');
            this.showNotification('WebSocket连接已建立', 'success');
        };

        this.websocket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleWebSocketMessage(message);
            } catch (error) {
                console.error('WebSocket消息解析失败:', error);
            }
        };

        this.websocket.onclose = () => {
            this.updateWebSocketStatus('disconnected', '连接断开');
            this.showNotification('WebSocket连接已断开', 'warning');
            
            // 尝试重连
            setTimeout(() => {
                this.connectWebSocket();
            }, 5000);
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket错误:', error);
            this.updateWebSocketStatus('error', '连接错误');
        };
    }

    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'file_progress':
                this.handleFileProgressMessage(message);
                break;
            case 'task_status':
                this.handleTaskStatusMessage(message);
                break;
            case 'notification':
                this.showNotification(message.message, 'info');
                break;
            case 'user_status':
                this.handleUserStatusMessage(message);
                break;
            default:
                console.log('未知WebSocket消息类型:', message.type);
        }
    }

    handleFileProgressMessage(message) {
        // 处理文件上传进度消息
        if (message.status === 'completed') {
            this.showNotification('文件上传完成', 'success');
        } else if (message.status === 'failed') {
            this.showNotification(`文件上传失败: ${message.error}`, 'error');
        }
    }

    handleTaskStatusMessage(message) {
        // 处理任务状态消息
        this.showNotification(`任务 ${message.task_id}: ${message.message}`, 'info');
    }

    handleUserStatusMessage(message) {
        // 处理用户状态消息
        console.log('用户状态更新:', message);
    }

    updateWebSocketStatus(status, text) {
        const statusText = document.getElementById('ws-status-text');
        const statusIndicator = document.getElementById('ws-status-indicator');
        
        statusText.textContent = text;
        
        statusIndicator.className = 'inline-block w-2 h-2 rounded-full ml-2';
        switch (status) {
            case 'connected':
                statusIndicator.classList.add('bg-green-500');
                break;
            case 'disconnected':
                statusIndicator.classList.add('bg-red-500');
                break;
            case 'error':
                statusIndicator.classList.add('bg-red-500');
                break;
            default:
                statusIndicator.classList.add('bg-yellow-500');
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `bg-white border-l-4 border-${this.getNotificationColor(type)}-400 p-4 shadow-lg rounded-r-lg max-w-sm`;
        
        notification.innerHTML = `
            <div class="flex items-center">
                <div class="flex-shrink-0">
                    <i class="fas fa-${this.getNotificationIcon(type)} text-${this.getNotificationColor(type)}-400"></i>
                </div>
                <div class="ml-3">
                    <p class="text-sm text-gray-700">${message}</p>
                </div>
                <div class="ml-auto pl-3">
                    <button onclick="this.parentElement.parentElement.parentElement.remove()" class="text-gray-400 hover:text-gray-600">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;

        const container = document.getElementById('notifications-container');
        container.appendChild(notification);

        // 自动移除通知
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    getNotificationColor(type) {
        switch (type) {
            case 'success': return 'green';
            case 'error': return 'red';
            case 'warning': return 'yellow';
            default: return 'blue';
        }
    }

    getNotificationIcon(type) {
        switch (type) {
            case 'success': return 'check-circle';
            case 'error': return 'exclamation-circle';
            case 'warning': return 'exclamation-triangle';
            default: return 'info-circle';
        }
    }

    // 工具函数
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDate(dateString) {
        if (!dateString) return '未知';
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN');
    }

    getAuthToken() {
        return localStorage.getItem('auth_token');
    }

    async checkAuth() {
        const token = this.getAuthToken();
        if (token) {
            try {
                const response = await fetch('/api/v1/auth/me', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (response.ok) {
                    this.user = await response.json();
                    this.updateUserInterface();
                } else {
                    this.logout();
                }
            } catch (error) {
                console.error('认证检查失败:', error);
                this.logout();
            }
        } else {
            this.showLoginModal();
        }
    }

    updateUserInterface() {
        // 更新用户界面显示
        const userMenuBtn = document.getElementById('user-menu-btn');
        if (this.user) {
            userMenuBtn.innerHTML = `<i class="fas fa-user-circle text-xl"></i>`;
        }
    }

    showLoginModal() {
        // 显示登录模态框
        this.showModal('登录', `
            <form id="login-form">
                <div class="mb-4">
                    <label class="block text-sm font-medium text-gray-700 mb-2">邮箱</label>
                    <input type="email" id="login-email" required class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                </div>
                <div class="mb-6">
                    <label class="block text-sm font-medium text-gray-700 mb-2">密码</label>
                    <input type="password" id="login-password" required class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                </div>
                <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">
                    登录
                </button>
            </form>
        `);

        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.login();
        });
    }

    async login() {
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        try {
            const response = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('auth_token', data.access_token);
                this.user = data.user;
                this.updateUserInterface();
                this.hideModal();
                this.showNotification('登录成功', 'success');
                this.connectWebSocket();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || '登录失败', 'error');
            }
        } catch (error) {
            console.error('登录失败:', error);
            this.showNotification('登录失败', 'error');
        }
    }

    logout() {
        localStorage.removeItem('auth_token');
        this.user = null;
        
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        this.updateWebSocketStatus('disconnected', '未连接');
        this.showNotification('已退出登录', 'info');
        this.showLoginModal();
    }

    showModal(title, content) {
        const modal = document.getElementById('modal-overlay');
        const modalContent = document.getElementById('modal-content');
        
        modalContent.innerHTML = `
            <div class="px-6 py-4 border-b border-gray-200">
                <div class="flex justify-between items-center">
                    <h3 class="text-lg font-semibold text-gray-900">${title}</h3>
                    <button onclick="app.hideModal()" class="text-gray-400 hover:text-gray-600">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="px-6 py-4">
                ${content}
            </div>
        `;
        
        modal.classList.remove('hidden');
    }

    hideModal() {
        document.getElementById('modal-overlay').classList.add('hidden');
    }

    // API调用函数
    async fetchStats() {
        const response = await fetch('/api/v1/documents/stats/summary', {
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        });
        return response.json();
    }

    async fetchRecentDocuments() {
        const response = await fetch('/api/v1/documents/?limit=5', {
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        });
        return response.json();
    }

    async fetchRecentLessonPlans() {
        const response = await fetch('/api/v1/lesson-plans/?limit=5', {
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        });
        return response.json();
    }

    async fetchDocuments() {
        const response = await fetch('/api/v1/documents/', {
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        });
        return response.json();
    }

    async fetchLessonPlans() {
        const response = await fetch('/api/v1/lesson-plans/', {
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        });
        return response.json();
    }

    // 其他功能函数
    async downloadDocument(id) {
        try {
            const response = await fetch(`/api/v1/documents/${id}/download`, {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (response.ok) {
                const blob = await response.blob();
                this.downloadBlob(blob, `document_${id}.pdf`);
            } else {
                throw new Error('下载失败');
            }
        } catch (error) {
            console.error('下载文档失败:', error);
            this.showNotification('下载失败', 'error');
        }
    }

    async editDocument(id) {
        // 实现文档编辑功能
        this.showNotification('文档编辑功能开发中', 'info');
    }

    async deleteDocument(id) {
        if (!confirm('确定要删除这个文档吗？')) return;

        try {
            const response = await fetch(`/api/v1/documents/${id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (response.ok) {
                this.showNotification('文档删除成功', 'success');
                this.loadDocuments();
            } else {
                throw new Error('删除失败');
            }
        } catch (error) {
            console.error('删除文档失败:', error);
            this.showNotification('删除失败', 'error');
        }
    }

    async viewLessonPlan(id) {
        // 实现教案查看功能
        this.showNotification('教案查看功能开发中', 'info');
    }

    async editLessonPlan(id) {
        // 实现教案编辑功能
        this.showNotification('教案编辑功能开发中', 'info');
    }

    async deleteLessonPlan(id) {
        if (!confirm('确定要删除这个教案吗？')) return;

        try {
            const response = await fetch(`/api/v1/lesson-plans/${id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (response.ok) {
                this.showNotification('教案删除成功', 'success');
                this.loadLessonPlans();
            } else {
                throw new Error('删除失败');
            }
        } catch (error) {
            console.error('删除教案失败:', error);
            this.showNotification('删除失败', 'error');
        }
    }

    async saveSettings() {
        const username = document.getElementById('username-setting').value;
        const email = document.getElementById('email-setting').value;
        const role = document.getElementById('role-setting').value;

        try {
            const response = await fetch('/api/v1/users/me', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    username,
                    email,
                    role
                })
            });

            if (response.ok) {
                this.showNotification('设置保存成功', 'success');
            } else {
                throw new Error('保存失败');
            }
        } catch (error) {
            console.error('保存设置失败:', error);
            this.showNotification('保存设置失败', 'error');
        }
    }

    loadUploadSection() {
        // 加载上传页面
        console.log('加载上传页面');
    }

    loadExportSection() {
        // 加载导出页面
        console.log('加载导出页面');
    }

    loadSearchSection() {
        // 加载搜索页面
        console.log('加载搜索页面');
    }

    async loadSettings() {
        try {
            const response = await fetch('/api/v1/users/me', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (response.ok) {
                const user = await response.json();
                document.getElementById('username-setting').value = user.username || '';
                document.getElementById('email-setting').value = user.email || '';
                document.getElementById('role-setting').value = user.role || 'student';
            }
        } catch (error) {
            console.error('加载设置失败:', error);
        }
    }
}

// 初始化应用
const app = new LessonPlannerApp();

