/**
 * SMS Transaction Parser Frontend
 * JavaScript functionality for the frontend interface
 */

function smsApp() {
    return {
        // Data properties
        smsText: '',
        isLoading: false,
        result: null,
        error: null,
        activeTab: 'parser',
        
        // Dashboard data
        balances: [],
        totalBalance: 0,
        reminders: [],
        transactions: [],
        
        // Subscription data
        subscriptions: [],
        subscriptionTotal: 0,
        
        // Insights data
        insights: {
            monthly_income: 0,
            monthly_spend: 0, 
            category_spend: {},
            average_transaction: 0,
            subscription_spend: 0,
            savings_rate: 0,
            day_of_week_spend: {}
        },
        selectedMonth: '',
        availableMonths: [],
        
        // Chart objects
        categoryChart: null,
        categoryPieChart: null,
        dayOfWeekChart: null,
        
        // API endpoint (change this to match your API server)
        apiUrl: 'http://localhost:5001',
        
        // Lifecycle hooks
        init() {
            // Generate available months for dropdown (current month and 5 previous months)
            const today = new Date();
            for (let i = 0; i < 6; i++) {
                const date = new Date(today.getFullYear(), today.getMonth() - i, 1);
                const monthValue = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
                const monthLabel = date.toLocaleString('default', { month: 'long', year: 'numeric' });
                
                this.availableMonths.push({
                    value: monthValue,
                    label: monthLabel
                });
            }
        },
        
        // Methods
        async processSMS() {
            if (!this.smsText) {
                return;
            }
            
            this.isLoading = true;
            this.error = null;
            
            try {
                const response = await fetch(`${this.apiUrl}/parse_sms`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        sms_text: this.smsText,
                        sender: '' // Adding empty sender parameter to match our API
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || errorData.error || 'Error processing SMS');
                }
                
                const rawData = await response.json();
                console.log("Raw parser response:", rawData);
                
                // Transform the response to match what the UI expects
                this.result = {
                    transaction: {
                        amount: rawData.transaction.amount,
                        transaction_type: rawData.transaction.type,
                        account_masked: rawData.transaction.account,
                        merchant_name: rawData.transaction.merchant,
                        date: rawData.transaction.date,
                        balance: rawData.transaction.balance
                    },
                    category: rawData.transaction.category || "Uncategorized",
                    fraud_detection: rawData.fraud_detection,
                    metadata: rawData.metadata
                };
                
                // Track this interaction for analytics if the function exists
                if (typeof this.trackAnalytics === 'function') {
                    this.trackAnalytics('sms_processed');
                } else {
                    console.log('Analytics tracking: sms_processed');
                }
                
            } catch (err) {
                console.error('Error:', err);
                this.error = err.message;
                alert(`Error: ${err.message}`);
            } finally {
                this.isLoading = false;
            }
        },
        
        async loadDashboardData() {
            try {
                // Load balances
                const balanceResponse = await fetch(`${this.apiUrl}/balance`);
                if (balanceResponse.ok) {
                    const balanceData = await balanceResponse.json();
                    this.balances = balanceData.accounts || [];
                    this.totalBalance = balanceData.total_balance || 0;
                }
                
                // Load reminders
                const reminderResponse = await fetch(`${this.apiUrl}/reminders`);
                if (reminderResponse.ok) {
                    const reminderData = await reminderResponse.json();
                    this.reminders = reminderData.reminders || [];
                }
                
                // Load transactions
                const transactionResponse = await fetch(`${this.apiUrl}/transactions`);
                if (transactionResponse.ok) {
                    const transactionData = await transactionResponse.json();
                    this.transactions = transactionData.transactions || [];
                }
                
                // Load insights for summary
                const insightsResponse = await fetch(`${this.apiUrl}/insights`);
                if (insightsResponse.ok) {
                    this.insights = await insightsResponse.json();
                    this.renderCategoryChart();
                }
            } catch (err) {
                console.error('Error loading dashboard data:', err);
            }
        },
        
        async loadSubscriptions() {
            try {
                const response = await fetch(`${this.apiUrl}/subscriptions`);
                if (response.ok) {
                    const data = await response.json();
                    this.subscriptions = data.subscriptions || [];
                    this.subscriptionTotal = data.total_monthly_cost || 0;
                }
            } catch (err) {
                console.error('Error loading subscriptions:', err);
            }
        },
        
        async loadInsights(month = this.selectedMonth) {
            try {
                const url = month ? `${this.apiUrl}/insights?month=${month}` : `${this.apiUrl}/insights`;
                const response = await fetch(url);
                
                if (response.ok) {
                    this.insights = await response.json();
                    
                    // Render charts with new data
                    this.$nextTick(() => {
                        this.renderCategoryPieChart();
                        this.renderDayOfWeekChart();
                    });
                }
            } catch (err) {
                console.error('Error loading insights:', err);
            }
        },
        
        renderCategoryChart() {
            // Destroy existing chart if it exists
            if (this.categoryChart) {
                this.categoryChart.destroy();
            }
            
            // Get categories and amounts
            const categories = Object.keys(this.insights.category_spend);
            const amounts = Object.values(this.insights.category_spend);
            
            // If no data, don't render
            if (categories.length === 0) return;
            
            // Create chart
            const ctx = document.getElementById('categoryChart');
            if (ctx) {
                this.categoryChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: categories,
                        datasets: [{
                            label: 'Spending by Category',
                            data: amounts,
                            backgroundColor: [
                                'rgba(54, 162, 235, 0.6)',
                                'rgba(255, 99, 132, 0.6)',
                                'rgba(255, 206, 86, 0.6)',
                                'rgba(75, 192, 192, 0.6)',
                                'rgba(153, 102, 255, 0.6)',
                                'rgba(255, 159, 64, 0.6)',
                                'rgba(199, 199, 199, 0.6)'
                            ],
                            borderColor: [
                                'rgba(54, 162, 235, 1)',
                                'rgba(255, 99, 132, 1)',
                                'rgba(255, 206, 86, 1)',
                                'rgba(75, 192, 192, 1)',
                                'rgba(153, 102, 255, 1)',
                                'rgba(255, 159, 64, 1)',
                                'rgba(199, 199, 199, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) {
                                        return '₹' + value.toLocaleString();
                                    }
                                }
                            }
                        },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return '₹' + context.parsed.y.toLocaleString();
                                    }
                                }
                            }
                        }
                    }
                });
            }
        },
        
        renderCategoryPieChart() {
            // Destroy existing chart if it exists
            if (this.categoryPieChart) {
                this.categoryPieChart.destroy();
            }
            
            // Get categories and amounts
            const categories = Object.keys(this.insights.category_spend);
            const amounts = Object.values(this.insights.category_spend);
            
            // If no data, don't render
            if (categories.length === 0) return;
            
            // Create chart
            const ctx = document.getElementById('categoryPieChart');
            if (ctx) {
                this.categoryPieChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: categories,
                        datasets: [{
                            data: amounts,
                            backgroundColor: [
                                'rgba(54, 162, 235, 0.8)',
                                'rgba(255, 99, 132, 0.8)',
                                'rgba(255, 206, 86, 0.8)',
                                'rgba(75, 192, 192, 0.8)',
                                'rgba(153, 102, 255, 0.8)',
                                'rgba(255, 159, 64, 0.8)',
                                'rgba(199, 199, 199, 0.8)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'right'
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.label || '';
                                        const value = '₹' + context.parsed.toLocaleString();
                                        const percentage = ((context.parsed / context.dataset.data.reduce((a, b) => a + b, 0)) * 100).toFixed(1) + '%';
                                        return `${label}: ${value} (${percentage})`;
                                    }
                                }
                            }
                        }
                    }
                });
            }
        },
        
        renderDayOfWeekChart() {
            // Destroy existing chart if it exists
            if (this.dayOfWeekChart) {
                this.dayOfWeekChart.destroy();
            }
            
            // Sort days of week in order
            const daysOrder = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
            const sortedData = daysOrder.map(day => this.insights.day_of_week_spend[day] || 0);
            
            // Create chart
            const ctx = document.getElementById('dayOfWeekChart');
            if (ctx) {
                this.dayOfWeekChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: daysOrder,
                        datasets: [{
                            label: 'Spending by Day',
                            data: sortedData,
                            backgroundColor: 'rgba(75, 192, 192, 0.6)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) {
                                        return '₹' + value.toLocaleString();
                                    }
                                }
                            }
                        },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return '₹' + context.parsed.y.toLocaleString();
                                    }
                                }
                            }
                        }
                    }
                });
            }
        },
        
        getTopSpendingDay() {
            const days = Object.keys(this.insights.day_of_week_spend);
            if (days.length === 0) return { day: 'None', amount: 0 };
            
            let topDay = '';
            let topAmount = 0;
            
            for (const day in this.insights.day_of_week_spend) {
                const amount = this.insights.day_of_week_spend[day];
                if (amount > topAmount) {
                    topAmount = amount;
                    topDay = day;
                }
            }
            
            return { day: topDay, amount: topAmount };
        },
        
        isToday(dateString) {
            const today = new Date().toISOString().split('T')[0];
            return dateString === today;
        },
        
        isNearDue(dateString) {
            const today = new Date();
            const dueDate = new Date(dateString);
            const diffDays = Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24));
            return diffDays <= 3 && diffDays >= 0;
        },
        
        formatDueDate(dateString) {
            const today = new Date();
            const dueDate = new Date(dateString);
            const diffDays = Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24));
            
            if (diffDays === 1) {
                return 'Due tomorrow';
            } else if (diffDays > 0) {
                return `Due in ${diffDays} days`;
            } else {
                return 'Overdue';
            }
        },
        
        selectSampleSMS(option) {
            switch(option) {
                case 1:
                    this.smsText = 'Your a/c XX1234 is debited with Rs.2,500.00 on 15-04-2023 at Swiggy. Available balance: Rs.45,000.00. If not you, call 18001234567.';
                    break;
                case 2:
                    this.smsText = 'Rs.15,000.00 credited to your account ending with XX5678 on 16-04-2023. Updated balance: Rs.35,000.00. Ref: NEFT/IMPS/RTG123456.';
                    break;
                case 3:
                    this.smsText = 'Thank you for shopping at Amazon. Rs.3,749.00 has been charged on your card ending with XX9876 on 17-04-2023. Txn ID: TXN123456.';
                    break;
                case 4:
                    this.smsText = 'URGENT: Your account will be blocked. Update KYC immediately to avoid service disruption. Click here: bit.ly/upd8kyc';
                    break;
                case 5:
                    this.smsText = 'Congratulations! You\'ve won a prize of Rs.10,00,000 in our lucky draw. To claim your prize, click here: tinyurl.com/claim-prize';
                    break;
                case 6:
                    this.smsText = 'Your Netflix subscription of Rs.649.00 has been charged to your HDFC Credit Card ending with XX5432 on 18-04-2023. Available balance: Rs.58,000.00.';
                    break;
                default:
                    break;
            }
        },
    };
}