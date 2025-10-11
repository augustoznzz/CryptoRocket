// Crypto Trading Analyzer - Frontend JavaScript (Análise das 12 Criptomoedas Selecionadas)

document.addEventListener('DOMContentLoaded', function() {
    const searchBtn = document.getElementById('searchBtn');
    const buttonText = document.querySelector('.button-text');
    const loadingSpinner = document.querySelector('.loading-spinner');
    const resultsSection = document.getElementById('results');
    const resultsContainer = document.getElementById('resultsContainer');
    const analysisInfo = document.getElementById('analysisInfo');
    const errorSection = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');

    // Enhanced dark background maintenance - CORRIGIDO
    function ensureDarkBackground() {
        // Force dark background on all viewport elements
        document.documentElement.style.background = 'linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 100%)';
        document.body.style.background = 'linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 100%)';
        
        // Force all main containers to have transparent background
        const containers = document.querySelectorAll('.container, .results-section, .results-container, main');
        containers.forEach(container => {
            container.style.background = 'transparent';
        });
        
        // Additional mobile-specific fixes
        if (window.innerWidth <= 768) {
            // Force full height coverage
            document.documentElement.style.minHeight = '100vh';
            document.documentElement.style.minHeight = '100dvh';
            document.body.style.minHeight = '100vh';
            document.body.style.minHeight = '100dvh';
            
            // Ensure particles canvas covers full screen - CORRIGIDO
            const particlesCanvas = document.getElementById('particles-canvas');
            if (particlesCanvas) {
                particlesCanvas.style.height = '100vh';
                particlesCanvas.style.height = '100dvh';
                // NÃO forçar opacity ou visibility - deixar o sistema natural
            }
            
            // Forçar cobertura extra para eliminar fundo branco
            forceExtraCoverage();
        }
    }
    
    // Função para forçar cobertura extra
    function forceExtraCoverage() {
        // Criar elemento de cobertura extra se não existir
        let extraCoverage = document.getElementById('extra-coverage');
        if (!extraCoverage) {
            extraCoverage = document.createElement('div');
            extraCoverage.id = 'extra-coverage';
            extraCoverage.style.cssText = `
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                height: 200px;
                background: linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 100%);
                z-index: -1;
                pointer-events: none;
            `;
            document.body.appendChild(extraCoverage);
        }
    }

    // Call on load and after results display
    ensureDarkBackground();
    
    // Additional mobile viewport handling
    function handleMobileViewport() {
        if (window.innerWidth <= 768) {
            // Force full coverage
            document.documentElement.style.height = '100%';
            document.body.style.height = '100%';
            
            // Prevent any white space
            document.body.style.overflow = 'hidden';
            document.documentElement.style.overflow = 'hidden';
            
            // Re-enable after a moment
            setTimeout(() => {
                document.body.style.overflow = '';
                document.documentElement.style.overflow = '';
            }, 100);
            
            // Forçar cobertura extra
            forceExtraCoverage();
        }
    }

    searchBtn.addEventListener('click', function() {
        startSearch();
    });

    function startSearch() {
        // Disable button and show loading
        searchBtn.disabled = true;
        buttonText.style.opacity = '0';
        loadingSpinner.style.display = 'block';
        
        // Hide previous results/errors
        resultsSection.style.display = 'none';
        errorSection.style.display = 'none';

        // Chamar função real da Netlify para análise das criptomoedas selecionadas
        fetch('/.netlify/functions/analyze-crypto', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                displayResults(data);
            } else {
                displayError(data.error || 'Erro desconhecido na análise');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (error.message.includes('HTTP')) {
                displayError(`Erro do servidor: ${error.message}`);
            } else {
                displayError('Erro de conexão. Verifique sua internet e tente novamente.');
            }
        })
        .finally(() => {
            // Re-enable button
            searchBtn.disabled = false;
            buttonText.style.opacity = '1';
            loadingSpinner.style.display = 'none';
        });
    }

    // Funções demo removidas - agora usando análise real da Netlify

    function displayResults(data) {
        resultsContainer.innerHTML = '';
        
        if (data.results && data.results.length > 0) {
            data.results.forEach((result, index) => {
                const card = createTradeCard(result, index + 1);
                resultsContainer.appendChild(card);
            });

            // Show analysis info
            analysisInfo.innerHTML = `
                <p><strong>Análise completa:</strong> ${data.total_analyzed} criptomoedas analisadas</p>
                <p><strong>Timestamp:</strong> ${data.timestamp}</p>
                <p><strong>Melhores oportunidades:</strong> Top 5 selecionadas (sempre mostrando as 5 melhores criptomoedas)</p>
                <p><em>💡 Análise técnica em tempo real com dados reais do mercado</em></p>
            `;

            resultsSection.style.display = 'block';
            
            // Ensure dark background after results are displayed
            setTimeout(ensureDarkBackground, 100);
            setTimeout(handleMobileViewport, 100);
        } else {
            displayError('Nenhuma oportunidade de trading encontrada no momento.');
        }
    }

    function createTradeCard(result, rank) {
        const card = document.createElement('div');
        card.className = 'trade-card';
        
        const signalTypeClass = result.type === 'LONG' ? 'signal-long' : (result.type === 'SHORT' ? 'signal-short' : 'signal-neutral');
        const emoji = result.type === 'LONG' ? '🔼' : '🔽';
        
        // Adicionar informações de preço se disponíveis
        const priceInfo = result.current_price ? `
            <div style="margin-bottom: 1rem; font-size: 0.9rem; color: #a0a0a0;">
                <span style="color: #ffffff; font-weight: 600;">$${result.current_price.toFixed(4)}</span>
            </div>
        ` : '';
        
        // Adicionar barra de confiança se disponível
        const confidenceBar = result.score ? `
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">
                <span style="font-size: 0.9rem; color: #00ff9d; font-weight: 600; min-width: 60px;">${Math.round(result.score * 100)}%</span>
                <div style="flex: 1; height: 8px; background: rgba(255, 255, 255, 0.1); border-radius: 4px; overflow: hidden;">
                    <div style="height: 100%; background: linear-gradient(135deg, #00ff9d 0%, #00b8ff 100%); width: ${Math.round(result.score * 100)}%; transition: width 0.3s ease;"></div>
                </div>
            </div>
        ` : '';
        
        card.innerHTML = `
            <div class="card-header">
                <div class="crypto-symbol">#${rank} ${result.symbol}/USDT</div>
                <div class="signal-type ${signalTypeClass}">${emoji} ${result.type}</div>
            </div>
            ${priceInfo}
            <div class="potential-gain">
                Potencial: +${result.potential_gain}%
            </div>
            ${confidenceBar}
            <div class="trade-details">${result.signal}</div>
        `;
        
        return card;
    }

    function displayError(message) {
        errorMessage.textContent = message;
        errorSection.style.display = 'block';
        
        // Ensure dark background after error display
        setTimeout(ensureDarkBackground, 100);
        setTimeout(handleMobileViewport, 100);
    }
    
    // Ensure dark background on window resize
    window.addEventListener('resize', function() {
        ensureDarkBackground();
        handleMobileViewport();
    });
    
    // Additional mobile-specific event listeners
    if ('ontouchstart' in window) {
        // Mobile device detected
        document.addEventListener('touchstart', ensureDarkBackground);
        document.addEventListener('touchend', ensureDarkBackground);
    }
});

// Add a subtle parallax effect to the background
document.addEventListener('mousemove', function(e) {
    const moveX = (e.clientX * -1 / 150);
    const moveY = (e.clientY * -1 / 150);
    
    document.body.style.backgroundPosition = `${moveX}px ${moveY}px`;
});

// Add keyboard shortcut (Space or Enter) to trigger search
document.addEventListener('keydown', function(e) {
    if ((e.code === 'Space' || e.code === 'Enter') && !document.getElementById('searchBtn').disabled) {
        e.preventDefault();
        document.getElementById('searchBtn').click();
    }
});