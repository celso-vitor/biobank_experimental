/* =========================================================
   SAMPLES PAGE JS - FINAL VERSION (EAV and Dynamic Storage)
========================================================= */

function getCsrfToken() {
    return document.querySelector("[name=csrfmiddlewaretoken]")?.value;
}

document.addEventListener("DOMContentLoaded", () => {

    /* --- 0. ELN INITIALIZATION (QUILL) --- */
    let quill = null;
    if(document.getElementById('eln-editor')) {
        quill = new Quill('#eln-editor', { theme: 'snow' });
    }

    /* --- 1. MAIN FORM (Validation & Submit) --- */
    const mainSampleForm = document.getElementById("mainSampleForm");
    if (mainSampleForm) {
        mainSampleForm.addEventListener("submit", function(e) {
            if (quill) {
                const notesInput = document.getElementById("scientific_notes_input");
                if(notesInput) notesInput.value = quill.root.innerHTML;
            }

            const biobankInputs = document.querySelectorAll('input[name="dist_biobank_id[]"]');
            if (biobankInputs.length === 0) {
                e.preventDefault();
                alert("Please add at least one physical Biobank location.");
                return false;
            }
        });
    }

    /* --- 2. TAGS --- */
    function initTagSystem() {
        document.querySelectorAll(".selectable-tag").forEach(chip => {
            if (chip.dataset.bound) return;
            chip.dataset.bound = "true";
            chip.addEventListener("click", function() {
                this.classList.toggle("selected");
                this.classList.toggle("bg-primary");
                this.classList.toggle("text-white");
                updateTagInputs();
            });
        });
    }

    function updateTagInputs() {
        const container = document.getElementById("tagHiddenInputs");
        if (!container) return;
        container.innerHTML = "";
        document.querySelectorAll(".selectable-tag.selected").forEach(chip => {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = "tags";
            input.value = chip.dataset.tagId;
            container.appendChild(input);
        });
    }

    function initTagAJAX() {
        const addTagForm = document.getElementById("addTagForm");
        const tagNameInput = document.getElementById("tagNameInput");
        const btnSave = document.getElementById("btnSaveTagAJAX");

        if (addTagForm && btnSave) {
            addTagForm.addEventListener("submit", function(e) {
                e.preventDefault();
                const tagName = tagNameInput.value.trim();
                if (!tagName) return;

                const fd = new FormData();
                fd.append('name', tagName);
                fd.append('csrfmiddlewaretoken', getCsrfToken());

                fetch('/ajax/add_tag/', { method: 'POST', body: fd })
                .then(res => res.json())
                .then(data => {
                    if (data.id) {
                        const container = document.getElementById("tagChipContainer");
                        if (container) {
                            const span = document.createElement("span");
                            span.className = "badge rounded-pill border selectable-tag m-1 p-2 selected bg-primary text-white";
                            span.dataset.tagId = data.id;
                            span.innerText = data.name;
                            span.style.cursor = "pointer";
                            container.appendChild(span);
                        }
                        tagNameInput.value = "";
                        const modal = bootstrap.Modal.getInstance(document.getElementById("addTagModal"));
                        if (modal) modal.hide();
                        initTagSystem();
                        updateTagInputs();
                    }
                });
            });
        }
    }

    /* --- 3. GENERIC KEYWORDS --- */
    function initKeywordSystem() {
        const btnSave = document.getElementById("btnSaveKeywordAJAX");
        if (btnSave) {
            btnSave.onclick = function(e) {
                e.preventDefault();
                const k = document.getElementById("keywordKey").value;
                const v = document.getElementById("keywordValue").value;
                if (!k || !v) return;

                const defaultMsg = document.querySelector('#keywordChipContainer .default-msg');
                if (defaultMsg) defaultMsg.style.display = 'none';

                const chip = document.createElement("span");
                chip.className = "badge bg-light text-dark border p-2 m-1 d-inline-flex align-items-center";
                chip.innerHTML = `<strong>${k}</strong>: ${v} <i class="bi bi-x ms-2 text-danger" style="cursor:pointer;"></i>`;

                const hidden = document.createElement("input");
                hidden.type = "hidden"; 
                hidden.name = "keyword_pairs"; 
                hidden.value = k + ":::" + v;

                chip.querySelector(".bi-x").onclick = () => { 
                    chip.remove(); hidden.remove(); 
                    if(document.querySelectorAll('#keywordChipContainer .badge').length === 0 && defaultMsg) {
                        defaultMsg.style.display = 'block';
                    }
                };
                
                document.getElementById("keywordChipContainer")?.appendChild(chip);
                document.getElementById("keywordHiddenInputs")?.appendChild(hidden);
                
                const modal = bootstrap.Modal.getInstance(document.getElementById("addKeywordModal"));
                if (modal) modal.hide();
                
                document.getElementById("keywordKey").value = ""; 
                document.getElementById("keywordValue").value = "";
            };
        }
    }

    /* --- 4. DYNAMIC STORAGE PATH BUILDER --- */
    function initDynamicStorage() {
        const container = document.getElementById('dynamicStorageContainer');
        const hiddenInput = document.getElementById('storage_location_hidden');
        const textInput = document.getElementById('storageInputVisual');

        if (!container || !textInput) return;

        let levels = [];

        function renderLevels() {
            container.querySelectorAll('.storage-tag-element').forEach(el => el.remove());

            levels.forEach((lvl, index) => {
                const badge = document.createElement('span');
                badge.className = 'badge bg-primary text-white storage-tag-element d-flex align-items-center py-1 px-2 shadow-sm';
                badge.innerHTML = `${lvl} <i class="bi bi-x-circle-fill ms-2" style="cursor:pointer; font-size: 0.85rem;" data-index="${index}"></i>`;
                
                container.insertBefore(badge, textInput);

                const arrow = document.createElement('span');
                arrow.className = 'text-muted storage-tag-element small fw-bold mx-1';
                arrow.innerHTML = '<i class="bi bi-chevron-right"></i>';
                container.insertBefore(arrow, textInput);
            });

            hiddenInput.value = levels.join(" > ");
            textInput.focus();
        }

        container.addEventListener('click', (e) => {
            if (e.target.tagName === 'I' && e.target.hasAttribute('data-index')) {
                levels.splice(e.target.dataset.index, 1);
                renderLevels();
            } else {
                textInput.focus();
            }
        });

        textInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                const val = this.value.trim().replace(/,$/, ''); 
                if (val) {
                    levels.push(val);
                    this.value = '';
                    renderLevels();
                }
            } else if (e.key === 'Backspace' && this.value === '' && levels.length > 0) {
                levels.pop();
                renderLevels();
            }
        });
    }

    /* --- 5. BIOBANK DISTRIBUTION --- */
    function initBiobankLogic() {
        const container = document.getElementById('selectedBiobanksContainer');
        const noMsg = document.getElementById('noBiobankMsg');
        const searchInput = document.getElementById('biobankSearch');
        
        if (searchInput) {
            searchInput.addEventListener('input', function(e) {
                const term = e.target.value.toLowerCase();
                document.querySelectorAll('.sheets-option').forEach(opt => {
                    const text = opt.dataset.name.toLowerCase();
                    opt.style.display = text.includes(term) ? 'flex' : 'none';
                });
            });
        }

        document.addEventListener('click', function(e) {
            const addBtn = e.target.closest('.btn-add-bb');
            if (addBtn) {
                e.preventDefault(); e.stopPropagation();
                const opt = addBtn.closest('.sheets-option');
                const bbId = opt.dataset.value;
                const bbName = opt.dataset.name;

                if (container.querySelector(`[data-bb-id="${bbId}"]`)) return;
                if (noMsg) noMsg.style.display = 'none';

                const selectedColId = document.querySelector('select[name="collection"]')?.value || "";

                const row = document.createElement('div');
                row.className = "d-flex align-items-center justify-content-between bg-white border rounded p-3 mb-2 bb-row shadow-sm";
                row.dataset.bbId = bbId;
                row.innerHTML = `
                    <div class="d-flex align-items-center flex-grow-1">
                        <i class="bi bi-building me-3 text-primary fs-5"></i>
                        <div class="flex-grow-1">
                            <span class="fw-bold d-block mb-1">${bbName}</span>
                            <input type="hidden" name="dist_biobank_id[]" value="${bbId}">
                            <input type="hidden" name="dist_collection_id[]" value="${selectedColId}">
                            <div class="d-flex gap-2 align-items-center">
                                <span class="text-muted small">Aliquots Qty:</span>
                                <input type="number" name="dist_quantity[]" class="form-control form-control-sm" value="1" min="1" style="width: 80px;">
                            </div>
                        </div>
                    </div>
                    <button type="button" class="btn btn-link text-danger remove-bb ms-3"><i class="bi bi-trash fs-5"></i></button>
                `;

                container.appendChild(row);
                
                const dropdownBtn = document.getElementById('biobankDropdownBtn');
                if(dropdownBtn) {
                    const bsDropdown = bootstrap.Dropdown.getInstance(dropdownBtn) || new bootstrap.Dropdown(dropdownBtn);
                    bsDropdown.hide();
                }
            }

            const removeBtn = e.target.closest('.remove-bb');
            if (removeBtn) {
                removeBtn.closest('.bb-row').remove();
                if (container.querySelectorAll('.bb-row').length === 0 && noMsg) noMsg.style.display = 'block';
            }
        });
    }

    /* --- 6. DYNAMIC TEMPLATES --- */
    function getFieldHTML(field) {
        const label = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        if (field === 'custom_organism_name') {
             return `
                <label class="section-label text-primary">Organism / Custom Description <span class="text-danger">*</span></label>
                <input type="text" name="${field}" class="form-control form-control-sm border-primary fw-bold" placeholder="Specify what this sample is..." required>
            `;
        }
        if (field.includes('sequence')) {
            return `
                <label class="section-label">${label}</label>
                <textarea name="${field}" class="form-control form-control-sm bg-white" placeholder="FASTA sequence..."></textarea>
            `;
        }
        if (field.includes('size_bp')) {
            return `
                <label class="section-label">${label}</label>
                <input type="number" name="${field}" class="form-control form-control-sm bg-white" placeholder="Ex: 4500" min="0">
            `;
        }
        if (field === 'temp_C') {
            return `
                <label class="section-label">${label} (°C)</label>
                <input type="number" step="0.1" name="${field}" class="form-control form-control-sm bg-white" placeholder="Ex: 37.5">
            `;
        }
        if (field === 'morphotype') {
            return `
                <label class="section-label">${label}</label>
                <select name="${field}" class="form-select form-select-sm bg-white">
                    <option value="">Select...</option>
                    <option value="myovirus">Myovirus</option>
                    <option value="siphovirus">Siphovirus</option>
                    <option value="podovirus">Podovirus</option>
                    <option value="other">Other</option>
                </select>
            `;
        }
        if (field === 'lifestyle') {
            return `
                <label class="section-label">${label}</label>
                <select name="${field}" class="form-select form-select-sm bg-white">
                    <option value="">Select...</option>
                    <option value="lytic">Lytic</option>
                    <option value="lysogenic">Lysogenic</option>
                </select>
            `;
        }
        if (field === 'genome_type') {
            return `
                <label class="section-label">${label}</label>
                <select name="${field}" class="form-select form-select-sm bg-white">
                    <option value="">Select...</option>
                    <option value="dsDNA">dsDNA</option>
                    <option value="ssDNA">ssDNA</option>
                    <option value="dsRNA">dsRNA</option>
                    <option value="ssRNA">ssRNA</option>
                </select>
            `;
        }
        if (field === 'vector_type') {
            return `
                <label class="section-label">${label}</label>
                <select name="${field}" class="form-select form-select-sm bg-white">
                    <option value="">Select...</option>
                    <option value="expression">Expression</option>
                    <option value="suicide">Suicide</option>
                    <option value="conjugation">Conjugation</option>
                    <option value="cloning">Cloning</option>
                </select>
            `;
        }
        return `
            <label class="section-label">${label}</label>
            <input type="text" name="${field}" class="form-control form-control-sm bg-white" placeholder="...">
        `;
    }

    function initDynamicTemplates() {
        const typeInput = document.getElementById('sampleTypeInput');
        const container = document.getElementById('dynamicTemplateContainer');
        const fieldsBox = document.getElementById('templateFields');
        const typeNameLabel = document.getElementById('templateTypeName');

        // UPDATED: Aligned with the new nomenclature requested
        const templates = {
            "Phage (Virus)": ["genus", "morphotype", "taxonomy", "lifestyle", "isolation_source", "genome_type", "genome_size_bp", "temp_C", "ncbi_accession"],
            "Bacterium (Host)": ["genus", "species", "strain", "genotype", "resistance_markers"],
            "Vector Backbone": ["vector_type", "induction_system", "vector_size_bp", "resistance_markers"],
            "Insert": ["insert_name", "insert_size_bp", "sequence"],
            "Plasmid (Backbone + Insert)": ["construction_name", "actual_resistances", "origin_lab"], // Backbone/Insert FKs typically rendered via standard Django Form outside EAV, but fields added here if needed.
            "Other": ["custom_organism_name"]
        };

        if(typeInput && container && fieldsBox) {
            typeInput.addEventListener('change', function() {
                const selectedType = this.options ? this.options[this.selectedIndex].text : this.value; 
                fieldsBox.innerHTML = ''; 
                
                if (templates[selectedType]) {
                    container.classList.remove('d-none');
                    if (typeNameLabel) typeNameLabel.innerText = selectedType;
                    
                    templates[selectedType].forEach(field => {
                        const col = document.createElement('div');
                        col.className = field === 'custom_organism_name' || field === 'sequence' ? 'col-md-6' : 'col-md-3';
                        col.innerHTML = getFieldHTML(field);
                        fieldsBox.appendChild(col);
                    });
                } else {
                    container.classList.add('d-none');
                }
            });
        }
    }

    /* --- 7. AUTO-PREFIXES DYNAMIC --- */
    function initPrefixLogic() {
        const typeInput = document.getElementById('sampleTypeInput');
        const identifierInput = document.getElementById('id_external_identifier'); // Confirme se o ID do HTML bate com este (gerado pelo Django forms)

        const prefixMap = {
            "Bacterium (Host)": "BAC-",
            "Phage (Virus)": "PHA-",
            "Vector Backbone": "BKB-",
            "Insert": "INS-",
            "Plasmid (Backbone + Insert)": "PLA-"
        };

        if (typeInput && identifierInput) {
            typeInput.addEventListener('change', function() {
                const selectedText = this.options ? this.options[this.selectedIndex].text : this.value;
                const newPrefix = prefixMap[selectedText] || '';

                const currentValue = identifierInput.value.trim();
                const isJustPrefix = Object.values(prefixMap).some(p => p === currentValue);

                // Só aplica o prefixo se o campo estiver vazio ou se o usuário ainda não tiver digitado nada além do prefixo antigo
                if (currentValue === '' || isJustPrefix) {
                    identifierInput.value = newPrefix;
                }
            });
        }
    }

    // --- INITIALIZATIONS ---
    initTagSystem();
    initTagAJAX();
    initKeywordSystem();
    initDynamicStorage();
    initBiobankLogic();
    initDynamicTemplates();
    initPrefixLogic();
});
