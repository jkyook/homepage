document.addEventListener('DOMContentLoaded', function() {
    const loadingMessage = document.getElementById('loadingMessage');
    const chartLoadingMessage = document.getElementById('chartLoadingMessage');
    const fileDropdown = document.getElementById('file_id');
    const strategySelect = document.getElementById('strategySelect');

    function fetchFiles() {
        loadingMessage.style.display = 'block'; // Show loading message

        fetch('/files')
            .then(response => response.json())
            .then(data => {
                loadingMessage.style.display = 'none'; // Hide loading message

                console.log('Received file data:', data); // 데이터 로깅
                if (!fileDropdown) {
                    console.error('Dropdown element not found');
                    return;
                }
                if (data.length === 0) {
                    console.warn('No file data received');
                    return;
                }
                fileDropdown.innerHTML = '<option value="">--Select a date--</option>'; // Reset options
                data.forEach(file => {
                    const option = document.createElement('option');
                    option.value = file.id;
                    option.textContent = file.date || file.name; // date가 없으면 name 사용
                    fileDropdown.appendChild(option);
                });
            })
            .catch(error => {
                loadingMessage.style.display = 'none'; // Hide loading message on error
                console.error('Error fetching file list:', error);
            });
    }

    fetchFiles(); // Initial file fetch

    strategySelect.addEventListener('change', function() {
        const selectedStrategy = strategySelect.value;
        if (selectedStrategy) {
            loadingMessage.style.display = 'block'; // Show loading message

            fetch('/files')
                .then(response => response.json())
                .then(data => {
                    loadingMessage.style.display = 'none'; // Hide loading message

                    console.log('Received file data:', data); // 데이터 로깅
                    const filteredData = data.filter(file => {
                        return selectedStrategy === 'bit' ? file.date.startsWith('B') : file.date.startsWith('K');
                    });
                    fileDropdown.innerHTML = '<option value="">--Select a date--</option>'; // Reset options
                    filteredData.forEach(file => {
                        const option = document.createElement('option');
                        option.value = file.id;
                        option.textContent = file.date || file.name; // date가 없으면 name 사용
                        fileDropdown.appendChild(option);
                    });
                })
                .catch(error => {
                    loadingMessage.style.display = 'none'; // Hide loading message on error
                    console.error('Error fetching file list:', error);
                });
        }
    });

    document.getElementById('fileForm').addEventListener('submit', function(event) {
        event.preventDefault();
        const fileId = fileDropdown.value;

        chartLoadingMessage.style.display = 'block'; // Show chart loading message

        fetch('/data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                'file_id': fileId
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            chartLoadingMessage.style.display = 'none'; // Hide chart loading message

            console.log('Data received from backend:', data);

            if (data.error) {
                console.error('Error:', data.error);
                return;
            }

            const labels = data.map(row => row['time']);
            const priceValues = data.map(row => row['price']);
            const np1Values = data.map(row => row['np1']);
            const np2Values = data.map(row => row['np2']);
            const prfValues = data.map(row => row['prf']);

            const ctx = document.getElementById('myChart').getContext('2d');

            // Ensure `window.myChart` is a valid Chart instance before calling destroy
            if (window.myChart && window.myChart instanceof Chart) {
                window.myChart.destroy();
            }

            window.myChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'price',
                            data: priceValues,
                            borderColor: '#4e73df',
                            backgroundColor: 'rgba(78, 115, 223, 0.2)',
                            borderWidth: 2,
                            pointRadius: 0.5,
                            fill: false,
                            yAxisID: 'y1'
                        },
                        {
                            label: 'long',
                            data: np1Values,
                            borderColor: '#28a745',  // 밝은 녹색으로 변경
                            backgroundColor: 'rgba(40, 167, 69, 0.2)',  // 밝은 녹색의 반투명 배경
                            borderWidth: 1,
                            pointRadius: 0.2,
                            fill: true,
                            yAxisID: 'y2'
                        },
                        {
                            label: 'short',
                            data: np2Values,
                            borderColor: '#b73d3d',  // 어두운 붉은색
                            backgroundColor: 'rgba(183, 61, 61, 0.2)',  // 어두운 붉은색의 반투명 배경
                            borderWidth: 1,
                            pointRadius: 0.2,
                            fill: true,
                            yAxisID: 'y2'
                        },
                        {
                            label: 'profit',
                            data: prfValues,
                            borderColor: '#f00',  // 빨간색으로 변경
                            backgroundColor: 'rgba(255, 0, 0, 0.2)',  // 빨간색의 반투명 배경
                            borderWidth: 3,
                            pointRadius: 0.7,
                            fill: false,
                            yAxisID: 'y2'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Time',
                                color: '#858796',
                                font: {
                                    size: 14
                                }
                            },
                            grid: {
                                display: false
                            }
                        },
                        y1: {
                            type: 'linear',
                            position: 'left',
                            title: {
                                display: true,
                                text: 'price',
                                color: '#4e73df',
                                font: {
                                    size: 14
                                }
                            },
                            ticks: {
                                beginAtZero: true,
                                color: '#4e73df'
                            },
                            grid: {
                                drawBorder: false,
                                borderDash: [2, 2],
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        },
                        y2: {
                            type: 'linear',
                            position: 'right',
                            title: {
                                display: true,
                                text: 'long, short, and profit',
                                color: '#e74a3b',
                                font: {
                                    size: 14
                                }
                            },
                            ticks: {
                                beginAtZero: true,
                                color: '#e74a3b'
                            },
                            grid: {
                                drawOnChartArea: false
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: '#858796',
                                font: {
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: '#f8f9fc',
                            bodyColor: '#858796',
                            borderColor: '#e3e6f0',
                            borderWidth: 1,
                            callbacks: {
                                label: function(tooltipItem) {
                                    return tooltipItem.dataset.label + ': ' + tooltipItem.raw;
                                }
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            chartLoadingMessage.style.display = 'none'; // Hide chart loading message on error
            console.error('Error fetching data:', error);
        });
    });
});
