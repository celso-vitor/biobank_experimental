/* =========================================================
   SAMPLES PAGE JS - VERSÃO FINAL REVISADA (FIXED FEEDBACK)
   Sincronizado com IDs de add_tag.html e Biobank Distribution
========================================================= */

function getCsrfToken() {
    return document.querySelector("[name=csrfmiddlewaretoken]")?.value;
}

document.addEventListener("DOMContentLoaded", () => {

    // 0. Carregar dados de coleções do JSON oculto no HTML
    let collectionsData = [];
    const collectionsScript = document.getElementById("collectionsData");
    if (collectionsScript) {
        try {
            collectionsData = JSON.parse(collectionsScript.textContent);
        } catch (e) { console.error("Erro coleções:", e); }
    }

    /* --- 1. FORM PRINCIPAL (Amostra) --- */
    const mainSampleForm = document.getElementById("mainSampleForm");
    if (mainSampleForm) {
        mainSampleForm.addEventListener("submit", function(e) {
            const quillEditor = document.querySelector('#eln-editor .ql-editor');
            if (quillEditor) {
                document.getElementById("scientific_notes_input").value = quillEditor.innerHTML;
            }

            if (document.querySelectorAll('input[name="dist_biobank_id[]"]').length === 0) {
                e.preventDefault();
                // Usa um alerta mais suave ou customizado se preferir, mas o alert funciona para validação
                alert("Please add at least one Biobank to the distribution list.");
            }
        });
    }

    /* --- 2. TAGS (INTERCEPTANDO O FORM EXISTENTE) --- */
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

        if (addTagForm) {
            addTagForm.addEventListener("submit", function(e) {
                e.preventDefault(); // Impede o reload da página

                const tagName = tagNameInput.value.trim();
                if (!tagName) return;

                // Feedback visual (Spinner)
                const spinner = btnSave.querySelector(".spinner-border");
                if (spinner) spinner.classList.remove("d-none");
                btnSave.disabled = true;

                const fd = new FormData();
                fd.append('name', tagName);
                fd.append('csrfmiddlewaretoken', getCsrfToken());

                fetch('/ajax/add_tag/', { method: 'POST', body: fd })
                .then(res => res.json())
                .then(data => {
                    if (data.id) {
                        // Adiciona o chip visualmente
                        const container = document.getElementById("tagChipContainer");
                        const span = document.createElement("span");
                        span.className = "badge rounded-pill border selectable-tag m-1 p-2 selected bg-primary text-white";
                        span.dataset.tagId = data.id;
                        span.innerText = data.name;
                        span.style.cursor = "pointer";
                        container.appendChild(span);

                        // Limpa e fecha
                        tagNameInput.value = "";
                        const modal = bootstrap.Modal.getInstance(document.getElementById("addTagModal"));
                        if (modal) modal.hide();

                        initTagSystem();
                        updateTagInputs();
                    } else {
                        alert("Error: " + (data.error || "Tag already exists or invalid."));
                    }
                })
                .catch(err => alert("Communication error."))
                .finally(() => {
                    if (spinner) spinner.classList.add("d-none");
                    btnSave.disabled = false;
                });
            });
        }
    }

    /* --- 3. BIOBANK & COLLECTIONS (FIXED EVENT DELEGATION) --- */
    function initBiobankLogic() {
        const container = document.getElementById('selectedBiobanksContainer');
        const noMsg = document.getElementById('noBiobankMsg');

        // Usa delegação de eventos no Document para pegar cliques em elementos criados dinamicamente
        document.addEventListener('click', function(e) {
            
            // --- ADD BIOBANK BUTTON ---
            const addBtn = e.target.closest('.btn-add-bb');
            if (addBtn) {
                e.preventDefault();
                e.stopPropagation();

                const opt = addBtn.closest('.sheets-option');
                const bbId = opt.dataset.value;
                const bbName = opt.dataset.name;

                // Evita duplicatas
                if (container.querySelector(`[data-bb-id="${bbId}"]`)) {
                    // Feedback opcional: Avisar que já foi adicionado
                    // alert("This Biobank is already selected."); 
                    return;
                }

                // Esconde msg "Nenhum selecionado"
                if (noMsg) noMsg.style.display = 'none';

                const filteredCols = collectionsData.filter(c => c.biobank_id == bbId);
                let colOptions = '<option value="">-- No Collection (Root) --</option>';
                filteredCols.forEach(c => colOptions += `<option value="${c.id}">${c.name}</option>`);

                const row = document.createElement('div');
                row.className = "d-flex align-items-center justify-content-between bg-white border rounded p-3 mb-2 bb-row shadow-sm";
                row.dataset.bbId = bbId;
                
                // Animação suave de entrada
                row.style.animation = "fadeIn 0.3s"; 

                row.innerHTML = `
                    <div class="d-flex align-items-center flex-grow-1">
                        <i class="bi bi-building me-3 text-primary fs-5"></i>
                        <div class="flex-grow-1">
                            <span class="fw-bold d-block mb-1">${bbName}</span>
                            <input type="hidden" name="dist_biobank_id[]" value="${bbId}">
                            <input type="hidden" name="dist_collection_id[]" class="col-hidden" value="">
                            <div class="d-flex gap-2">
                                <div class="input-group input-group-sm" style="width: 100px;">
                                    <span class="input-group-text">Qty</span>
                                    <input type="number" name="dist_quantity[]" class="form-control" value="1" min="1">
                                </div>
                                <select class="form-select form-select-sm col-selector" style="max-width: 250px;">
                                    ${colOptions}
                                </select>
                            </div>
                        </div>
                    </div>
                    <button type="button" class="btn btn-link text-danger remove-bb"><i class="bi bi-trash"></i></button>
                `;

                // Bind do select
                const sel = row.querySelector('.col-selector');
                const hid = row.querySelector('.col-hidden');
                sel.onchange = () => hid.value = sel.value;

                container.appendChild(row);
            }

            // --- REMOVE BIOBANK BUTTON ---
            const removeBtn = e.target.closest('.remove-bb');
            if (removeBtn) {
                const row = removeBtn.closest('.bb-row');
                row.remove();
                
                // Se não houver mais linhas, mostra a mensagem novamente
                if (container.querySelectorAll('.bb-row').length === 0) {
                    if (noMsg) noMsg.style.display = 'block';
                }
            }
        });
    }

    function initKeywordSystem() {
        const btnSave = document.getElementById("btnSaveKeywordAJAX");
        if (btnSave) {
            btnSave.onclick = function(e) {
                e.preventDefault();
                const k = document.getElementById("keywordKey").value;
                const v = document.getElementById("keywordValue").value;
                if (!k || !v) return;

                const chip = document.createElement("span");
                chip.className = "badge bg-light text-dark border p-2 m-1 d-inline-flex align-items-center";
                chip.innerHTML = `<strong>${k}</strong>: ${v} <i class="bi bi-x ms-2 text-danger" style="cursor:pointer;"></i>`;

                const hidden = document.createElement("input");
                hidden.type = "hidden"; hidden.name = "keyword_pairs"; hidden.value = k + ":::" + v;

                chip.querySelector(".bi-x").onclick = () => { chip.remove(); hidden.remove(); };
                document.getElementById("keywordChipContainer").appendChild(chip);
                document.getElementById("keywordHiddenInputs").appendChild(hidden);
                bootstrap.Modal.getInstance(document.getElementById("addKeywordModal")).hide();
                document.getElementById("keywordKey").value = ""; document.getElementById("keywordValue").value = "";
            };
        }
    }

    initTagSystem();
    initTagAJAX();
    initKeywordSystem();
    initBiobankLogic();
});
