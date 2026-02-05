/**
 * Convoso Insight Lens - Content Script
 * 
 * APPROACH: Inject calculated columns directly into Convoso's native tables.
 * - Keeps exact same report layout
 * - Adds APPT % and LXFER % columns inline
 * - No separate dashboard - overlay toggle only
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

const INSIGHT_CONFIG = {
    enabled: true,
    // Column names to look for (case-insensitive)
    columns: {
        contacts: ['contacts', 'contact'],
        appt: ['appt', 'status \'appt', 'status \'appt - appointment scheduled\'', 'appointment'],
        lxfer: ['lxfer', 'status \'lxfer', 'status \'lxfer - live transfer\'', 'live transfer'],
        success: ['success', 'all success', 'total success'],
        dialed: ['dialed']
    },
    // Hidden columns (by header text)
    hiddenColumns: [],
    // Lensed column visibility (6 columns total)
    lensedColumns: {
        apptContacts: true,
        apptCalls: true,
        lxferContacts: true,
        lxferCalls: true,
        successContacts: true,
        successCalls: true
    },
    // Color scheme by metric type (not performance-based)
    colors: {
        appt: { bg: '#dbeafe', text: '#1e40af' },      // Blue for APPT
        lxfer: { bg: '#fce7f3', text: '#9d174d' },     // Pink for LXFER
        success: { bg: '#d1fae5', text: '#065f46' }    // Green for Success
    }
};

let columnsInjected = false;
let settingsPanelVisible = false;

// =============================================================================
// STORAGE - Load and save user preferences
// =============================================================================

/**
 * Load settings from chrome.storage.local
 */
async function loadSettings() {
    try {
        const result = await chrome.storage.local.get('insightLens');
        if (result.insightLens) {
            if (result.insightLens.hiddenColumns) {
                INSIGHT_CONFIG.hiddenColumns = result.insightLens.hiddenColumns;
            }
            if (result.insightLens.lensedColumns) {
                // Merge with defaults to handle new columns added in updates
                INSIGHT_CONFIG.lensedColumns = {
                    ...INSIGHT_CONFIG.lensedColumns,
                    ...result.insightLens.lensedColumns
                };
            }
        }
        console.log('[Insight Lens] Settings loaded:', INSIGHT_CONFIG);
    } catch (e) {
        console.log('[Insight Lens] Using default settings');
    }
}

/**
 * Save settings to chrome.storage.local
 */
async function saveSettings() {
    try {
        await chrome.storage.local.set({
            insightLens: {
                hiddenColumns: INSIGHT_CONFIG.hiddenColumns,
                lensedColumns: INSIGHT_CONFIG.lensedColumns
            }
        });
        console.log('[Insight Lens] Settings saved');
    } catch (e) {
        console.error('[Insight Lens] Failed to save settings:', e);
    }
}

// =============================================================================
// UTILITIES
// =============================================================================

/**
 * Parse numeric values from strings like "31.73%", "1,200", etc.
 */
function parseNum(str) {
    if (!str || typeof str !== 'string') return 0;
    const clean = str.replace(/[%$,]/g, '').trim();
    const num = parseFloat(clean);
    return isNaN(num) ? 0 : num;
}

/**
 * Format as percentage with 2 decimals
 */
function formatPct(num) {
    if (isNaN(num) || !isFinite(num)) return '—';
    return num.toFixed(2) + '%';
}

/**
 * Get color style based on metric type (not performance-based)
 * Colors differentiate APPT vs LXFER vs Success columns
 */
function getColorStyle(metricType) {
    const colors = INSIGHT_CONFIG.colors[metricType] || { bg: '#f3f4f6', text: '#374151' };
    return `background: ${colors.bg}; color: ${colors.text};`;
}

/**
 * Find column index by matching header text (case-insensitive, partial match)
 */
function findColumnIndex(headers, searchTerms) {
    for (let i = 0; i < headers.length; i++) {
        const headerText = headers[i].toLowerCase().trim();
        for (const term of searchTerms) {
            if (headerText.includes(term.toLowerCase())) {
                return i;
            }
        }
    }
    return -1;
}

// =============================================================================
// COLUMN INJECTION
// =============================================================================

/**
 * Process a single table - inject 6 Lensed columns:
 * APPT%(C), APPT%(D), LXFER%(C), LXFER%(D), SUCCESS%(C), SUCCESS%(D)
 * (C) = of Contacts, (D) = of Dialed/Calls
 */
function processTable(table) {
    const headerRow = table.querySelector('thead tr');
    if (!headerRow) return;

    // Get all header texts
    const headerCells = Array.from(headerRow.querySelectorAll('th'));
    const headers = headerCells.map(th => th.innerText.trim());

    // Check if we already injected columns
    if (headers.some(h => h.includes('APPT%(C)') || h.includes('LXFER%(C)') || h.includes('SUCCESS%(C)'))) {
        return; // Already processed
    }

    // Find required columns
    const contactsIdx = findColumnIndex(headers, INSIGHT_CONFIG.columns.contacts);
    const apptIdx = findColumnIndex(headers, INSIGHT_CONFIG.columns.appt);
    const lxferIdx = findColumnIndex(headers, INSIGHT_CONFIG.columns.lxfer);
    const successIdx = findColumnIndex(headers, INSIGHT_CONFIG.columns.success);
    const dialedIdx = findColumnIndex(headers, INSIGHT_CONFIG.columns.dialed);

    // Need at least contacts OR dialed column to calculate percentages
    if (contactsIdx === -1 && dialedIdx === -1) {
        console.log('[Insight Lens] Skipping table - no Contacts or Dialed column found');
        return;
    }

    console.log('[Insight Lens] Processing table with columns:', { contactsIdx, apptIdx, lxferIdx, successIdx, dialedIdx });

    // Build insertions array - 6 Lensed columns
    const insertions = [];

    // SUCCESS columns (insert last so they appear at the end)
    if (successIdx !== -1) {
        // SUCCESS % of Dialed (Calls)
        if (dialedIdx !== -1 && INSIGHT_CONFIG.lensedColumns.successCalls) {
            insertions.push({
                afterIdx: successIdx,
                headerText: 'SUCCESS%(D)',
                headerTitle: 'All Success % of Dialed (Calls)',
                metricType: 'success',
                calculate: (cells) => {
                    const dialed = parseNum(cells[dialedIdx]?.innerText);
                    const success = parseNum(cells[successIdx]?.innerText);
                    return dialed > 0 ? (success / dialed) * 100 : 0;
                },
                cssClass: 'insight-calc-col insight-success-calls',
                lensedKey: 'successCalls'
            });
        }
        // SUCCESS % of Contacts
        if (contactsIdx !== -1 && INSIGHT_CONFIG.lensedColumns.successContacts) {
            insertions.push({
                afterIdx: successIdx,
                headerText: 'SUCCESS%(C)',
                headerTitle: 'All Success % of Contacts',
                metricType: 'success',
                calculate: (cells) => {
                    const contacts = parseNum(cells[contactsIdx]?.innerText);
                    const success = parseNum(cells[successIdx]?.innerText);
                    return contacts > 0 ? (success / contacts) * 100 : 0;
                },
                cssClass: 'insight-calc-col insight-success-contacts',
                lensedKey: 'successContacts'
            });
        }
    }

    // LXFER columns
    if (lxferIdx !== -1) {
        // LXFER % of Dialed (Calls)
        if (dialedIdx !== -1 && INSIGHT_CONFIG.lensedColumns.lxferCalls) {
            insertions.push({
                afterIdx: lxferIdx,
                headerText: 'LXFER%(D)',
                headerTitle: 'LXFER % of Dialed (Calls)',
                metricType: 'lxfer',
                calculate: (cells) => {
                    const dialed = parseNum(cells[dialedIdx]?.innerText);
                    const lxfer = parseNum(cells[lxferIdx]?.innerText);
                    return dialed > 0 ? (lxfer / dialed) * 100 : 0;
                },
                cssClass: 'insight-calc-col insight-lxfer-calls',
                lensedKey: 'lxferCalls'
            });
        }
        // LXFER % of Contacts
        if (contactsIdx !== -1 && INSIGHT_CONFIG.lensedColumns.lxferContacts) {
            insertions.push({
                afterIdx: lxferIdx,
                headerText: 'LXFER%(C)',
                headerTitle: 'LXFER % of Contacts',
                metricType: 'lxfer',
                calculate: (cells) => {
                    const contacts = parseNum(cells[contactsIdx]?.innerText);
                    const lxfer = parseNum(cells[lxferIdx]?.innerText);
                    return contacts > 0 ? (lxfer / contacts) * 100 : 0;
                },
                cssClass: 'insight-calc-col insight-lxfer-contacts',
                lensedKey: 'lxferContacts'
            });
        }
    }

    // APPT columns
    if (apptIdx !== -1) {
        // APPT % of Dialed (Calls)
        if (dialedIdx !== -1 && INSIGHT_CONFIG.lensedColumns.apptCalls) {
            insertions.push({
                afterIdx: apptIdx,
                headerText: 'APPT%(D)',
                headerTitle: 'APPT % of Dialed (Calls)',
                metricType: 'appt',
                calculate: (cells) => {
                    const dialed = parseNum(cells[dialedIdx]?.innerText);
                    const appt = parseNum(cells[apptIdx]?.innerText);
                    return dialed > 0 ? (appt / dialed) * 100 : 0;
                },
                cssClass: 'insight-calc-col insight-appt-calls',
                lensedKey: 'apptCalls'
            });
        }
        // APPT % of Contacts
        if (contactsIdx !== -1 && INSIGHT_CONFIG.lensedColumns.apptContacts) {
            insertions.push({
                afterIdx: apptIdx,
                headerText: 'APPT%(C)',
                headerTitle: 'APPT % of Contacts',
                metricType: 'appt',
                calculate: (cells) => {
                    const contacts = parseNum(cells[contactsIdx]?.innerText);
                    const appt = parseNum(cells[apptIdx]?.innerText);
                    return contacts > 0 ? (appt / contacts) * 100 : 0;
                },
                cssClass: 'insight-calc-col insight-appt-contacts',
                lensedKey: 'apptContacts'
            });
        }
    }

    if (insertions.length === 0) {
        console.log('[Insight Lens] No columns to inject based on current settings');
        return;
    }

    // Sort insertions by index descending so we insert from right to left
    // (prevents index shifting issues)
    insertions.sort((a, b) => b.afterIdx - a.afterIdx);

    // Inject header cells with metric-type coloring
    insertions.forEach(ins => {
        const newTh = document.createElement('th');
        newTh.innerText = ins.headerText;
        newTh.title = ins.headerTitle;
        newTh.className = ins.cssClass;
        const headerColors = INSIGHT_CONFIG.colors[ins.metricType] || { bg: '#f3f4f6', text: '#374151' };
        newTh.style.cssText = `background: ${headerColors.bg}; color: ${headerColors.text}; font-weight: 600; min-width: 70px; text-align: center; cursor: help;`;
        
        const afterCell = headerCells[ins.afterIdx];
        if (afterCell && afterCell.nextSibling) {
            headerRow.insertBefore(newTh, afterCell.nextSibling);
        } else {
            headerRow.appendChild(newTh);
        }
    });

    // Inject data cells for each row with metric-type coloring (not performance-based)
    const bodyRows = table.querySelectorAll('tbody tr');
    bodyRows.forEach(row => {
        const cells = Array.from(row.querySelectorAll('td'));
        if (cells.length === 0) return;

        insertions.forEach(ins => {
            const value = ins.calculate(cells);
            const newTd = document.createElement('td');
            newTd.innerText = formatPct(value);
            newTd.className = ins.cssClass;
            
            // Color coding by metric type (APPT=blue, LXFER=pink, SUCCESS=green)
            newTd.style.cssText = `${getColorStyle(ins.metricType)} font-weight: 600; text-align: center;`;

            const afterCell = cells[ins.afterIdx];
            if (afterCell && afterCell.nextSibling) {
                row.insertBefore(newTd, afterCell.nextSibling);
            } else {
                row.appendChild(newTd);
            }
        });
    });

    columnsInjected = true;
    console.log('[Insight Lens] Injected 6 Lensed columns into table');
}

/**
 * Scan page for all data tables and process them
 */
function scanAndInject() {
    if (!INSIGHT_CONFIG.enabled) return;

    // Find all tables on the page
    const tables = document.querySelectorAll('table');
    
    tables.forEach(table => {
        // Only process tables that look like data tables (have thead)
        if (table.querySelector('thead')) {
            processTable(table);
            applyColumnVisibility(table);
        }
    });

    // Update toggle button state
    updateToggleState();
}

/**
 * Apply column visibility based on user preferences (both original and lensed)
 */
function applyColumnVisibility(table) {
    const headerRow = table.querySelector('thead tr');
    if (!headerRow) return;

    const headerCells = Array.from(headerRow.querySelectorAll('th'));
    const bodyRows = table.querySelectorAll('tbody tr');

    // Map lensed column keys to header text
    const lensedHeaderMap = {
        'APPT%(C)': 'apptContacts',
        'APPT%(D)': 'apptCalls',
        'LXFER%(C)': 'lxferContacts',
        'LXFER%(D)': 'lxferCalls',
        'SUCCESS%(C)': 'successContacts',
        'SUCCESS%(D)': 'successCalls'
    };

    headerCells.forEach((th, colIndex) => {
        const headerText = th.innerText.trim();
        
        // Check if it's a lensed column
        const lensedKey = lensedHeaderMap[headerText];
        let isHidden = false;
        
        if (lensedKey) {
            // Lensed column - check lensedColumns config
            isHidden = !INSIGHT_CONFIG.lensedColumns[lensedKey];
        } else {
            // Original column - check hiddenColumns array
            isHidden = INSIGHT_CONFIG.hiddenColumns.includes(headerText);
        }
        
        // Hide/show header
        th.style.display = isHidden ? 'none' : '';
        
        // Hide/show corresponding data cells
        bodyRows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells[colIndex]) {
                cells[colIndex].style.display = isHidden ? 'none' : '';
            }
        });
    });
}

/**
 * Apply visibility for a specific lensed column immediately
 */
function applyLensedColumnVisibility(key, isVisible) {
    // Map key to header text for more reliable matching
    const headerMap = {
        apptContacts: 'APPT%(C)',
        apptCalls: 'APPT%(D)',
        lxferContacts: 'LXFER%(C)',
        lxferCalls: 'LXFER%(D)',
        successContacts: 'SUCCESS%(C)',
        successCalls: 'SUCCESS%(D)'
    };
    
    const headerText = headerMap[key];
    if (!headerText) return;
    
    // Find columns by header text across all tables
    document.querySelectorAll('table').forEach(table => {
        const headerRow = table.querySelector('thead tr');
        if (!headerRow) return;

        const headerCells = Array.from(headerRow.querySelectorAll('th'));
        const bodyRows = table.querySelectorAll('tbody tr');

        headerCells.forEach((th, colIndex) => {
            if (th.innerText.trim() === headerText) {
                th.style.display = isVisible ? '' : 'none';
                bodyRows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells[colIndex]) {
                        cells[colIndex].style.display = isVisible ? '' : 'none';
                    }
                });
            }
        });
    });
}

/**
 * Apply visibility for an original column immediately by header text
 */
function applyOriginalColumnVisibility(headerText, isVisible) {
    document.querySelectorAll('table').forEach(table => {
        const headerRow = table.querySelector('thead tr');
        if (!headerRow) return;

        const headerCells = Array.from(headerRow.querySelectorAll('th'));
        const bodyRows = table.querySelectorAll('tbody tr');

        headerCells.forEach((th, colIndex) => {
            if (th.innerText.trim() === headerText) {
                th.style.display = isVisible ? '' : 'none';
                bodyRows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells[colIndex]) {
                        cells[colIndex].style.display = isVisible ? '' : 'none';
                    }
                });
            }
        });
    });
}

/**
 * Get all column headers from all tables on page
 */
function getAllColumnHeaders() {
    const allHeaders = new Set();
    const tables = document.querySelectorAll('table thead tr');
    
    tables.forEach(headerRow => {
        const cells = headerRow.querySelectorAll('th');
        cells.forEach(th => {
            const text = th.innerText.trim();
            if (text) allHeaders.add(text);
        });
    });
    
    return Array.from(allHeaders);
}

// =============================================================================
// OVERLAY TOGGLE
// =============================================================================

/**
 * Create floating On/Off toggle button
 */
function createOnOffButton() {
    if (document.getElementById('insight-lens-onoff')) return;

    const btn = document.createElement('button');
    btn.id = 'insight-lens-onoff';
    btn.innerHTML = `
        <span style="display: flex; align-items: center; gap: 8px;">
            <span class="ils-toggle-switch" style="
                width: 36px;
                height: 20px;
                background: #059669;
                border-radius: 10px;
                position: relative;
                transition: background 0.2s;
            ">
                <span class="ils-toggle-knob" style="
                    position: absolute;
                    top: 2px;
                    left: 18px;
                    width: 16px;
                    height: 16px;
                    background: white;
                    border-radius: 50%;
                    transition: left 0.2s;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
                "></span>
            </span>
            <span class="ils-toggle-label">Lens ON</span>
        </span>
    `;
    btn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 99999;
        padding: 8px 14px;
        background: #1f2937;
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transition: all 0.2s;
    `;

    btn.addEventListener('mouseenter', () => {
        btn.style.transform = 'scale(1.05)';
    });

    btn.addEventListener('mouseleave', () => {
        btn.style.transform = 'scale(1)';
    });

    btn.addEventListener('click', toggleInsightLens);

    document.body.appendChild(btn);
}

/**
 * Create floating Dashboard button
 */
function createDashboardButton() {
    if (document.getElementById('insight-lens-dashboard')) return;

    const btn = document.createElement('button');
    btn.id = 'insight-lens-dashboard';
    btn.innerHTML = '📊 Dashboard';
    btn.style.cssText = `
        position: fixed;
        bottom: 120px;
        right: 20px;
        z-index: 99999;
        padding: 10px 16px;
        background: #2563eb;
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transition: all 0.2s;
    `;

    btn.addEventListener('mouseenter', () => {
        btn.style.background = '#1d4ed8';
        btn.style.transform = 'scale(1.05)';
    });

    btn.addEventListener('mouseleave', () => {
        btn.style.background = '#2563eb';
        btn.style.transform = 'scale(1)';
    });

    btn.addEventListener('click', toggleOverlay);

    document.body.appendChild(btn);
}

/**
 * Toggle the insight lens on/off
 */
function toggleInsightLens() {
    INSIGHT_CONFIG.enabled = !INSIGHT_CONFIG.enabled;
    
    if (INSIGHT_CONFIG.enabled) {
        scanAndInject();
        showNotification('Insight Lens enabled - Calculated columns added');
    } else {
        // Remove injected columns
        removeInjectedColumns();
        showNotification('Insight Lens disabled');
    }
    
    updateToggleState();
}

/**
 * Update toggle button appearance
 */
function updateToggleState() {
    const btn = document.getElementById('insight-lens-onoff');
    if (!btn) return;

    const toggleSwitch = btn.querySelector('.ils-toggle-switch');
    const toggleKnob = btn.querySelector('.ils-toggle-knob');
    const toggleLabel = btn.querySelector('.ils-toggle-label');
    
    if (!toggleSwitch || !toggleKnob || !toggleLabel) return;

    if (INSIGHT_CONFIG.enabled) {
        toggleSwitch.style.background = '#059669';
        toggleKnob.style.left = '18px';
        toggleLabel.textContent = 'Lens ON';
    } else {
        toggleSwitch.style.background = '#6b7280';
        toggleKnob.style.left = '2px';
        toggleLabel.textContent = 'Lens OFF';
    }
}

/**
 * Remove all injected columns
 */
function removeInjectedColumns() {
    document.querySelectorAll('.insight-calc-col').forEach(el => el.remove());
    columnsInjected = false;
}

/**
 * Show a brief notification
 */
function showNotification(message) {
    const notif = document.createElement('div');
    notif.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 999999;
        padding: 12px 20px;
        background: #1f2937;
        color: white;
        border-radius: 8px;
        font-size: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        animation: slideIn 0.3s ease;
    `;
    notif.innerText = message;
    document.body.appendChild(notif);

    setTimeout(() => {
        notif.style.opacity = '0';
        notif.style.transition = 'opacity 0.3s';
        setTimeout(() => notif.remove(), 300);
    }, 2000);
}

// =============================================================================
// SETTINGS GEAR BUTTON & COLUMN VISIBILITY PANEL
// =============================================================================

/**
 * Create the floating gear button for column settings
 */
function createSettingsButton() {
    if (document.getElementById('insight-lens-settings-btn')) return;

    const btn = document.createElement('button');
    btn.id = 'insight-lens-settings-btn';
    btn.innerHTML = '⚙️ Columns';
    btn.style.cssText = `
        position: fixed;
        bottom: 70px;
        right: 20px;
        z-index: 99999;
        padding: 10px 16px;
        background: #4b5563;
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transition: all 0.2s;
    `;

    btn.addEventListener('mouseenter', () => {
        btn.style.background = '#374151';
        btn.style.transform = 'scale(1.05)';
    });

    btn.addEventListener('mouseleave', () => {
        btn.style.background = '#4b5563';
        btn.style.transform = 'scale(1)';
    });

    btn.addEventListener('click', toggleSettingsPanel);

    document.body.appendChild(btn);
}

/**
 * Toggle settings panel visibility
 */
function toggleSettingsPanel() {
    const panel = document.getElementById('insight-lens-settings-panel');
    if (panel) {
        panel.remove();
        settingsPanelVisible = false;
    } else {
        createSettingsPanel();
        settingsPanelVisible = true;
    }
}

/**
 * Create the settings panel with column checkboxes
 */
function createSettingsPanel() {
    if (document.getElementById('insight-lens-settings-panel')) return;

    const panel = document.createElement('div');
    panel.id = 'insight-lens-settings-panel';
    panel.style.cssText = `
        position: fixed;
        bottom: 170px;
        right: 20px;
        z-index: 99999;
        width: 280px;
        max-height: calc(100vh - 190px);
        background: white;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        overflow: hidden;
        display: flex;
        flex-direction: column;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    `;

    // Get all column headers
    const allHeaders = getAllColumnHeaders();
    
    // Separate lensed columns from original columns
    const lensedHeaders = allHeaders.filter(h => 
        h.includes('%(C)') || h.includes('%(D)')
    );
    const originalHeaders = allHeaders.filter(h => 
        !h.includes('%(C)') && !h.includes('%(D)')
    );

    panel.innerHTML = `
        <div style="padding: 12px 16px; background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); color: white; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 600;">Column Visibility</span>
            <button id="ils-settings-close" style="background: none; border: none; color: white; font-size: 18px; cursor: pointer;">✕</button>
        </div>
        <div style="flex: 1; overflow-y: auto; padding: 12px 16px;">
            <div style="margin-bottom: 12px;">
                <div style="font-size: 11px; font-weight: 600; color: #92400e; background: #fef3c7; padding: 4px 8px; border-radius: 4px; margin-bottom: 8px;">
                    🔬 LENSED COLUMNS
                </div>
                ${buildLensedCheckboxes()}
            </div>
            <div>
                <div style="font-size: 11px; font-weight: 600; color: #1e40af; background: #dbeafe; padding: 4px 8px; border-radius: 4px; margin-bottom: 8px;">
                    📊 ORIGINAL COLUMNS
                </div>
                ${buildOriginalCheckboxes(originalHeaders)}
            </div>
        </div>
        <div style="padding: 12px 16px; border-top: 1px solid #e5e7eb; background: #f9fafb;">
            <button id="ils-apply-settings" style="width: 100%; padding: 8px; background: #2563eb; color: white; border: none; border-radius: 6px; font-weight: 600; cursor: pointer;">
                Apply & Save
            </button>
        </div>
    `;

    document.body.appendChild(panel);

    // Event listeners
    document.getElementById('ils-settings-close').addEventListener('click', toggleSettingsPanel);
    document.getElementById('ils-apply-settings').addEventListener('click', applySettingsFromPanel);

    // Checkbox change handlers for lensed columns - apply immediately and save
    panel.querySelectorAll('.ils-lensed-checkbox').forEach(cb => {
        cb.addEventListener('change', (e) => {
            const key = e.target.dataset.key;
            INSIGHT_CONFIG.lensedColumns[key] = e.target.checked;
            applyLensedColumnVisibility(key, e.target.checked);
            saveSettings();
        });
    });

    // Checkbox change handlers for original columns - apply immediately and save
    panel.querySelectorAll('.ils-original-checkbox').forEach(cb => {
        cb.addEventListener('change', (e) => {
            const header = e.target.dataset.header;
            if (e.target.checked) {
                INSIGHT_CONFIG.hiddenColumns = INSIGHT_CONFIG.hiddenColumns.filter(h => h !== header);
            } else {
                if (!INSIGHT_CONFIG.hiddenColumns.includes(header)) {
                    INSIGHT_CONFIG.hiddenColumns.push(header);
                }
            }
            applyOriginalColumnVisibility(header, e.target.checked);
            saveSettings();
        });
    });
}

/**
 * Build checkboxes for lensed columns (6 total)
 */
function buildLensedCheckboxes() {
    const lensedItems = [
        { key: 'apptContacts', label: 'APPT% (Contacts)', color: INSIGHT_CONFIG.colors.appt },
        { key: 'apptCalls', label: 'APPT% (Calls)', color: INSIGHT_CONFIG.colors.appt },
        { key: 'lxferContacts', label: 'LXFER% (Contacts)', color: INSIGHT_CONFIG.colors.lxfer },
        { key: 'lxferCalls', label: 'LXFER% (Calls)', color: INSIGHT_CONFIG.colors.lxfer },
        { key: 'successContacts', label: 'SUCCESS% (Contacts)', color: INSIGHT_CONFIG.colors.success },
        { key: 'successCalls', label: 'SUCCESS% (Calls)', color: INSIGHT_CONFIG.colors.success }
    ];

    return lensedItems.map(item => `
        <label style="display: flex; align-items: center; padding: 6px 0; cursor: pointer;">
            <input type="checkbox" 
                   class="ils-lensed-checkbox" 
                   data-key="${item.key}" 
                   ${INSIGHT_CONFIG.lensedColumns[item.key] ? 'checked' : ''}
                   style="margin-right: 8px; width: 16px; height: 16px;">
            <span style="font-size: 13px; padding: 2px 6px; border-radius: 3px; background: ${item.color.bg}; color: ${item.color.text};">${item.label}</span>
        </label>
    `).join('');
}

/**
 * Build checkboxes for original columns
 */
function buildOriginalCheckboxes(headers) {
    if (headers.length === 0) {
        return '<p style="font-size: 12px; color: #6b7280;">Load a report to see columns</p>';
    }

    return headers.map(header => `
        <label style="display: flex; align-items: center; padding: 6px 0; cursor: pointer;">
            <input type="checkbox" 
                   class="ils-original-checkbox" 
                   data-header="${escapeHtml(header)}" 
                   ${!INSIGHT_CONFIG.hiddenColumns.includes(header) ? 'checked' : ''}
                   style="margin-right: 8px; width: 16px; height: 16px;">
            <span style="font-size: 13px;">${escapeHtml(header)}</span>
        </label>
    `).join('');
}

/**
 * Apply settings from the panel and save
 */
async function applySettingsFromPanel() {
    const panel = document.getElementById('insight-lens-settings-panel');
    if (!panel) return;

    // Collect hidden original columns
    const hiddenCols = [];
    panel.querySelectorAll('.ils-original-checkbox').forEach(cb => {
        if (!cb.checked) {
            hiddenCols.push(cb.dataset.header);
        }
    });
    INSIGHT_CONFIG.hiddenColumns = hiddenCols;

    // Collect lensed column settings
    panel.querySelectorAll('.ils-lensed-checkbox').forEach(cb => {
        INSIGHT_CONFIG.lensedColumns[cb.dataset.key] = cb.checked;
    });

    // Save to storage
    await saveSettings();

    // Re-apply: remove old columns and re-inject
    removeInjectedColumns();
    scanAndInject();

    // Apply visibility to all tables
    document.querySelectorAll('table').forEach(table => {
        applyColumnVisibility(table);
    });

    showNotification('Column settings saved!');
    toggleSettingsPanel();
}

// =============================================================================
// MUTATION OBSERVER - Handle dynamic Angular updates
// =============================================================================

let debounceTimer;
const observer = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        if (INSIGHT_CONFIG.enabled) {
            scanAndInject();
        }
    }, 500);
});

// =============================================================================
// MESSAGE HANDLER - Communication with popup
// =============================================================================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    switch (request.action) {
        case 'openOverlay':
            showOverlay();
            sendResponse({ status: 'ok' });
            break;
            
        case 'toggle':
            toggleInsightLens();
            sendResponse({ status: 'ok', enabled: INSIGHT_CONFIG.enabled });
            break;
            
        case 'getStatus':
            sendResponse({ 
                status: 'ok', 
                enabled: INSIGHT_CONFIG.enabled, 
                columnsInjected 
            });
            break;
            
        case 'refresh':
            removeInjectedColumns();
            scanAndInject();
            sendResponse({ status: 'ok' });
            break;
            
        default:
            sendResponse({ status: 'error', message: 'Unknown action' });
    }
    return true;
});

// =============================================================================
// OVERLAY DASHBOARD
// =============================================================================

let overlayVisible = false;

/**
 * Create the overlay dashboard
 */
function createOverlayDashboard() {
    if (document.getElementById('insight-lens-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'insight-lens-overlay';
    overlay.innerHTML = `
        <div class="ils-overlay-backdrop"></div>
        <div class="ils-overlay-panel">
            <div class="ils-header">
                <h1>📊 Convoso Insight Lens</h1>
                <div class="ils-header-actions">
                    <button id="ils-refresh-btn" class="ils-btn">↻ Refresh</button>
                    <button id="ils-export-btn" class="ils-btn">📥 Export CSV</button>
                    <button id="ils-close-btn" class="ils-btn ils-btn-close">✕</button>
                </div>
            </div>
            <div class="ils-content">
                <div class="ils-loading">Loading data...</div>
                <div class="ils-table-container" style="display:none;">
                    <table class="ils-table">
                        <thead id="ils-table-head"></thead>
                        <tbody id="ils-table-body"></tbody>
                    </table>
                </div>
            </div>
            <div class="ils-footer">
                <span><strong>%(C)</strong> = ÷ Contacts</span>
                <span><strong>%(D)</strong> = ÷ Dialed (Calls)</span>
                <span><strong>Contact %</strong> = Contacts ÷ Dialed</span>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Event listeners
    document.getElementById('ils-close-btn').addEventListener('click', hideOverlay);
    document.getElementById('ils-refresh-btn').addEventListener('click', () => populateOverlay());
    document.getElementById('ils-export-btn').addEventListener('click', exportCSV);
    document.querySelector('.ils-overlay-backdrop').addEventListener('click', hideOverlay);

    // Inject styles
    injectOverlayStyles();
}

/**
 * Inject overlay CSS
 */
function injectOverlayStyles() {
    if (document.getElementById('ils-overlay-styles')) return;

    const style = document.createElement('style');
    style.id = 'ils-overlay-styles';
    style.textContent = `
        #insight-lens-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 999999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        #insight-lens-overlay.visible {
            display: block;
        }
        .ils-overlay-backdrop {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
        }
        .ils-overlay-panel {
            position: absolute;
            top: 20px;
            left: 20px;
            right: 20px;
            bottom: 20px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.25);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .ils-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 24px;
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
            color: white;
        }
        .ils-header h1 {
            font-size: 20px;
            margin: 0;
        }
        .ils-header-actions {
            display: flex;
            gap: 8px;
        }
        .ils-btn {
            padding: 8px 14px;
            background: rgba(255,255,255,0.2);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: background 0.2s;
        }
        .ils-btn:hover {
            background: rgba(255,255,255,0.3);
        }
        .ils-btn-close {
            background: #ef4444;
            font-size: 16px;
            padding: 8px 12px;
        }
        .ils-btn-close:hover {
            background: #dc2626;
        }
        .ils-content {
            flex: 1;
            overflow: auto;
            padding: 0;
        }
        .ils-loading {
            text-align: center;
            padding: 60px;
            color: #6b7280;
            font-size: 16px;
        }
        .ils-table-container {
            overflow: auto;
            height: 100%;
        }
        .ils-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }
        .ils-table th, .ils-table td {
            padding: 8px 10px;
            border: 1px solid #e5e7eb;
            text-align: left;
            white-space: nowrap;
        }
        .ils-table thead th {
            background: #f3f4f6;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        .ils-table .ils-list-header {
            background: #dbeafe;
            color: #1e40af;
            text-align: center;
            font-weight: 700;
            border-left: 3px solid #3b82f6;
        }
        .ils-table .ils-metric-header {
            font-size: 10px;
            color: #6b7280;
            background: #f9fafb;
        }
        .ils-table .ils-agent-cell {
            font-weight: 600;
            background: #fafafa;
            position: sticky;
            left: 0;
            z-index: 5;
            border-right: 2px solid #d1d5db;
        }
        .ils-table .ils-divider {
            border-left: 3px solid #3b82f6;
        }
        .ils-table .ils-pct {
            background: #fef9c3;
            font-weight: 600;
            text-align: right;
        }
        .ils-table .ils-pct-good {
            background: #bbf7d0;
            color: #166534;
        }
        .ils-table .ils-pct-bad {
            background: #fecaca;
            color: #991b1b;
        }
        .ils-table tbody tr:hover td {
            background: #f0f9ff;
        }
        .ils-table tbody tr:hover .ils-agent-cell {
            background: #e0f2fe;
        }
        .ils-footer {
            display: flex;
            gap: 24px;
            padding: 12px 24px;
            background: #f8fafc;
            border-top: 1px solid #e5e7eb;
            font-size: 12px;
            color: #64748b;
        }
    `;
    document.head.appendChild(style);
}

/**
 * Show the overlay dashboard
 */
function showOverlay() {
    createOverlayDashboard();
    document.getElementById('insight-lens-overlay').classList.add('visible');
    overlayVisible = true;
    populateOverlay();
}

/**
 * Hide the overlay dashboard
 */
function hideOverlay() {
    const overlay = document.getElementById('insight-lens-overlay');
    if (overlay) {
        overlay.classList.remove('visible');
    }
    overlayVisible = false;
}

/**
 * Toggle overlay visibility
 */
function toggleOverlay() {
    if (overlayVisible) {
        hideOverlay();
    } else {
        showOverlay();
    }
}

/**
 * Populate the overlay with data
 */
function populateOverlay() {
    const loading = document.querySelector('.ils-loading');
    const tableContainer = document.querySelector('.ils-table-container');
    const thead = document.getElementById('ils-table-head');
    const tbody = document.getElementById('ils-table-body');

    loading.style.display = 'block';
    tableContainer.style.display = 'none';

    // Extract data from all tables on the page
    const data = extractAllTableData();
    
    if (data.agents.size === 0) {
        loading.textContent = 'No agent data found. Make sure a report is loaded.';
        return;
    }

    // Build pivot table - filter out "All" list as it's redundant with TOTALS
    const lists = Array.from(data.lists)
        .filter(listName => listName.toLowerCase() !== 'all')
        .sort();
    // Updated metrics to include all 6 Lensed columns
    const metrics = ['Dialed', 'Contacts', 'Contact%', 'APPT', 'APPT%(C)', 'APPT%(D)', 'LXFER', 'LXFER%(C)', 'LXFER%(D)', 'Success', 'SUCCESS%(C)', 'SUCCESS%(D)'];

    // Header row 1: List names
    let header1 = '<tr><th rowspan="2" class="ils-agent-cell">Agent</th>';
    header1 += `<th colspan="${metrics.length}" class="ils-list-header">TOTALS</th>`;
    lists.forEach(list => {
        const shortName = list.length > 25 ? list.substring(0, 25) + '...' : list;
        header1 += `<th colspan="${metrics.length}" class="ils-list-header">${escapeHtml(shortName)}</th>`;
    });
    header1 += '</tr>';

    // Header row 2: Metric names
    let header2 = '<tr>';
    const metricHeaders = metrics.map(m => `<th class="ils-metric-header">${m}</th>`).join('');
    header2 += metricHeaders; // Totals
    lists.forEach(() => {
        header2 += metricHeaders;
    });
    header2 += '</tr>';

    thead.innerHTML = header1 + header2;

    // Data rows
    let bodyHtml = '';
    const sortedAgents = Array.from(data.agents.entries())
        .sort((a, b) => b[1].totals.dialed - a[1].totals.dialed);

    sortedAgents.forEach(([agentName, agentData]) => {
        bodyHtml += '<tr>';
        bodyHtml += `<td class="ils-agent-cell">${escapeHtml(agentName)}</td>`;
        
        // Totals
        bodyHtml += renderMetricCells(agentData.totals, false);

        // Each list
        lists.forEach(listName => {
            const listData = agentData.lists.get(listName) || { dialed: 0, contacts: 0, appt: 0, lxfer: 0 };
            bodyHtml += renderMetricCells(listData, true);
        });

        bodyHtml += '</tr>';
    });

    tbody.innerHTML = bodyHtml;

    loading.style.display = 'none';
    tableContainer.style.display = 'block';
}

/**
 * Render metric cells for a data object
 * Includes all 6 Lensed columns with metric-type coloring
 */
function renderMetricCells(data, addDivider) {
    const contactPct = data.dialed > 0 ? (data.contacts / data.dialed) * 100 : 0;
    // % of Contacts
    const apptPctC = data.contacts > 0 ? (data.appt / data.contacts) * 100 : 0;
    const lxferPctC = data.contacts > 0 ? (data.lxfer / data.contacts) * 100 : 0;
    const successPctC = data.contacts > 0 ? ((data.success || 0) / data.contacts) * 100 : 0;
    // % of Dialed (Calls)
    const apptPctD = data.dialed > 0 ? (data.appt / data.dialed) * 100 : 0;
    const lxferPctD = data.dialed > 0 ? (data.lxfer / data.dialed) * 100 : 0;
    const successPctD = data.dialed > 0 ? ((data.success || 0) / data.dialed) * 100 : 0;

    const divider = addDivider ? 'ils-divider' : '';
    
    // Metric-type colors (not performance-based)
    const apptColor = INSIGHT_CONFIG.colors.appt;
    const lxferColor = INSIGHT_CONFIG.colors.lxfer;
    const successColor = INSIGHT_CONFIG.colors.success;

    return `
        <td class="${divider}">${data.dialed}</td>
        <td>${data.contacts}</td>
        <td class="ils-pct">${contactPct.toFixed(1)}%</td>
        <td>${data.appt}</td>
        <td style="background:${apptColor.bg};color:${apptColor.text};font-weight:600;text-align:right;">${apptPctC.toFixed(1)}%</td>
        <td style="background:${apptColor.bg};color:${apptColor.text};font-weight:600;text-align:right;">${apptPctD.toFixed(1)}%</td>
        <td>${data.lxfer}</td>
        <td style="background:${lxferColor.bg};color:${lxferColor.text};font-weight:600;text-align:right;">${lxferPctC.toFixed(1)}%</td>
        <td style="background:${lxferColor.bg};color:${lxferColor.text};font-weight:600;text-align:right;">${lxferPctD.toFixed(1)}%</td>
        <td>${data.success || 0}</td>
        <td style="background:${successColor.bg};color:${successColor.text};font-weight:600;text-align:right;">${successPctC.toFixed(1)}%</td>
        <td style="background:${successColor.bg};color:${successColor.text};font-weight:600;text-align:right;">${successPctD.toFixed(1)}%</td>
    `;
}

/**
 * Extract all table data from the page
 */
function extractAllTableData() {
    const agents = new Map();
    const lists = new Set();

    document.querySelectorAll('table').forEach(table => {
        const headerRow = table.querySelector('thead tr');
        if (!headerRow) return;

        const headerCells = Array.from(headerRow.querySelectorAll('th'));
        const headers = headerCells.map(th => th.innerText.trim().toLowerCase());

        // Find column indices
        const userIdx = headers.findIndex(h => h === 'user' || h === 'agent');
        const listIdx = headers.findIndex(h => h.includes('list'));
        const dialedIdx = findColumnIndex(headers, ['dialed']);
        const contactsIdx = findColumnIndex(headers, ['contacts', 'contact']);
        const apptIdx = findColumnIndex(headers, ['appt', 'appointment']);
        const lxferIdx = findColumnIndex(headers, ['lxfer', 'live transfer']);
        const successIdx = findColumnIndex(headers, ['success', 'all success', 'total success']);

        if (userIdx === -1) return;

        table.querySelectorAll('tbody tr').forEach(row => {
            const cells = Array.from(row.querySelectorAll('td'));
            if (cells.length < 3) return;

            const agentName = cells[userIdx]?.innerText.trim() || 'Unknown';
            const listName = listIdx !== -1 ? (cells[listIdx]?.innerText.trim() || 'Default') : 'All';
            
            lists.add(listName);

            if (!agents.has(agentName)) {
                agents.set(agentName, {
                    lists: new Map(),
                    totals: { dialed: 0, contacts: 0, appt: 0, lxfer: 0, success: 0 }
                });
            }

            const agentData = agents.get(agentName);
            const dialed = dialedIdx !== -1 ? parseNum(cells[dialedIdx]?.innerText) : 0;
            const contacts = contactsIdx !== -1 ? parseNum(cells[contactsIdx]?.innerText) : 0;
            const appt = apptIdx !== -1 ? parseNum(cells[apptIdx]?.innerText) : 0;
            const lxfer = lxferIdx !== -1 ? parseNum(cells[lxferIdx]?.innerText) : 0;
            const success = successIdx !== -1 ? parseNum(cells[successIdx]?.innerText) : 0;

            // Aggregate per list
            if (!agentData.lists.has(listName)) {
                agentData.lists.set(listName, { dialed: 0, contacts: 0, appt: 0, lxfer: 0, success: 0 });
            }
            const listData = agentData.lists.get(listName);
            listData.dialed += dialed;
            listData.contacts += contacts;
            listData.appt += appt;
            listData.lxfer += lxfer;
            listData.success += success;

            // Aggregate totals
            agentData.totals.dialed += dialed;
            agentData.totals.contacts += contacts;
            agentData.totals.appt += appt;
            agentData.totals.lxfer += lxfer;
            agentData.totals.success += success;
        });
    });

    return { agents, lists };
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

/**
 * Export data to CSV
 * Includes all 6 Lensed metrics: APPT%(C), APPT%(D), LXFER%(C), LXFER%(D), SUCCESS%(C), SUCCESS%(D)
 */
function exportCSV() {
    const data = extractAllTableData();
    // Filter out "All" list from export as well
    const lists = Array.from(data.lists)
        .filter(listName => listName.toLowerCase() !== 'all')
        .sort();
    
    let csv = 'Agent,List,Dialed,Contacts,Contact%,APPT,APPT%(C),APPT%(D),LXFER,LXFER%(C),LXFER%(D),Success,SUCCESS%(C),SUCCESS%(D)\n';
    
    data.agents.forEach((agentData, agentName) => {
        agentData.lists.forEach((listData, listName) => {
            // Skip "All" list
            if (listName.toLowerCase() === 'all') return;
            
            const contactPct = listData.dialed > 0 ? (listData.contacts / listData.dialed) * 100 : 0;
            // % of Contacts
            const apptPctC = listData.contacts > 0 ? (listData.appt / listData.contacts) * 100 : 0;
            const lxferPctC = listData.contacts > 0 ? (listData.lxfer / listData.contacts) * 100 : 0;
            const successPctC = listData.contacts > 0 ? ((listData.success || 0) / listData.contacts) * 100 : 0;
            // % of Dialed (Calls)
            const apptPctD = listData.dialed > 0 ? (listData.appt / listData.dialed) * 100 : 0;
            const lxferPctD = listData.dialed > 0 ? (listData.lxfer / listData.dialed) * 100 : 0;
            const successPctD = listData.dialed > 0 ? ((listData.success || 0) / listData.dialed) * 100 : 0;
            
            csv += `"${agentName}","${listName}",${listData.dialed},${listData.contacts},${contactPct.toFixed(2)}%,${listData.appt},${apptPctC.toFixed(2)}%,${apptPctD.toFixed(2)}%,${listData.lxfer},${lxferPctC.toFixed(2)}%,${lxferPctD.toFixed(2)}%,${listData.success || 0},${successPctC.toFixed(2)}%,${successPctD.toFixed(2)}%\n`;
        });
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `convoso-insight-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    
    showNotification('CSV exported!');
}

// =============================================================================
// INITIALIZATION
// =============================================================================

console.log('[Insight Lens] Content script loaded');

/**
 * Initialize the extension
 */
async function initialize() {
    // Load saved settings first
    await loadSettings();
    
    // Create floating buttons (order: On/Off at bottom, then Columns, then Dashboard)
    createOnOffButton();
    createSettingsButton();
    createDashboardButton();

    // Initial scan for inline columns (with delay for Angular to render)
    setTimeout(scanAndInject, 1000);

    // Start observing for dynamic content
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    console.log('[Insight Lens] Initialization complete');
}

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
`;
document.head.appendChild(style);

// Run initialization
initialize();
