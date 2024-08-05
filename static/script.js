let chart;

function updateChart() {
    fetch('/prices')
        .then(response => response.json())
        .then(data => {
            const labels = data.map(item => new Date(item.timestamp).toLocaleTimeString());
            const prices = data.map(item => item.price);

            if (chart) {
                chart.data.labels = labels;
                chart.data.datasets[0].data = prices;
                chart.update();
            } else {
                const ctx = document.getElementById('bitcoinChart').getContext('2d');
                chart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: '비트코인 가격 (USDT)',
                            data: prices,
                            borderColor: 'rgb(75, 192, 192)',
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            x: {
                                reverse: true
                            }
                        }
                    }
                });
            }
        });
}

updateChart();
setInterval(updateChart, 5000);