document.addEventListener('DOMContentLoaded', function() {
    fetch('/files')
        .then(response => response.json())
        .then(data => {
            console.log('Received file data:', data);  // 데이터 로깅
            const dropdown = document.getElementById('file_id');
            if (!dropdown) {
                console.error('Dropdown element not found');
                return;
            }
            if (data.length === 0) {
                console.warn('No file data received');
                return;
            }
            data.forEach(file => {
                const option = document.createElement('option');
                option.value = file.id;
                option.textContent = file.date || file.name;  // date가 없으면 name 사용
                dropdown.appendChild(option);
            });
        })
        .catch(error => console.error('Error fetching file list:', error));

    document.getElementById('fileForm').addEventListener('submit', function(event) {
        event.preventDefault();
        const fileId = document.getElementById('file_id').value;

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
                            label: 'Bitcoin Price',
                            data: priceValues,
                            borderColor: '#4e73df',
                            backgroundColor: 'rgba(78, 115, 223, 0.2)',
                            borderWidth: 2,
                            pointRadius: 0.5,
                            fill: false,
                            yAxisID: 'y1'
                        },
                        {
                            label: 'NP1',
                            data: np1Values,
                            borderColor: '#e74a3b',
                            backgroundColor: 'rgba(231, 74, 59, 0.2)',
                            borderWidth: 2,  // 줄인 선 두께
                            pointRadius: 0.5,  // 점 크기 줄이기
                            fill: true,
                            yAxisID: 'y2'
                        },
                        {
                            label: 'NP2',
                            data: np2Values,
                            borderColor: '#1cc88a',
                            backgroundColor: 'rgba(28, 200, 138, 0.2)',
                            borderWidth: 2,  // 줄인 선 두께
                            pointRadius: 0.5,  // 점 크기 줄이기
                            fill: true,
                            yAxisID: 'y2'
                        },
                        {
                            label: 'PRF',
                            data: prfValues,
                            borderColor: '#858796',
                            backgroundColor: 'rgba(133, 135, 150, 0.2)',
                            borderWidth: 2,
                            pointRadius: 1,
                            fill: false,
                            yAxisID: 'y2'
                        }
                    ]
                },
                options: {
                    responsive: true,  // 차트가 화면 크기에 맞게 조정됨
                    maintainAspectRatio: true,  // 차트의 종횡비 유지
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
                                text: 'Bitcoin Price',
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
                                text: 'NP1, NP2, and PRF',
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
        .catch(error => console.error('Error fetching data:', error));
    });
});
