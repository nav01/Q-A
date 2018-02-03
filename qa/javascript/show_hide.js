/*
    Functions to show and hide stuff through buttons.
*/
function showAddForm(e){
    var form = document.getElementById(e.data.a);
    var divShowAdd = document.getElementById(e.data.b);
    var divHideAdd = document.getElementById(e.data.c);
    form.style.display = 'block';
    divHideAdd.style.display = 'block';
    divShowAdd.style.display = 'none';
}
function hideAddForm(e){
    var form = document.getElementById(e.data.a);
    var divShowAdd = document.getElementById(e.data.b);
    var divHideAdd = document.getElementById(e.data.c);
    form.style.display = 'none';
    divHideAdd.style.display = 'none';
    divShowAdd.style.display = 'block';
}
