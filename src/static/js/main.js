var saved_rows = {}

function jobToggle(id) {
    var row = document.querySelector("#job-" + id);
    let idElem = row.querySelector(".job-id");
    let statusElem = row.querySelector(".job-status");
    if (saved_rows[id] == undefined) {
        saved_rows[id] = row.cloneNode(true);
        row.querySelectorAll("td").forEach(elem => {
            if (elem != idElem) {
                elem.innerHTML = "...";
                if (elem != statusElem) {
                    elem.style.backgroundColor = "gray";
                }
            }    
        });
    } else {
        row.innerHTML = saved_rows[id].innerHTML;
        saved_rows[id] = undefined;
    }
}

window.onload = function() {
    let table_rows = document.querySelectorAll(".row");
    table_rows.forEach(row => {
        let id = row.getAttribute("id").substr(4);
        let statusElem = row.querySelector(".job-status");
        let status = statusElem.innerHTML;
        if (status != "running") {
            jobToggle(id);
        }
    });
}
