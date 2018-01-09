function showAddForm(a,b,c){
    var divAddForm = document.getElementById(a);
    var divShowAdd = document.getElementById(b);
    var divHideAdd = document.getElementById(c);
    divAddForm.style.display='block';
    divHideAdd.style.display='block';
    divShowAdd.style.display = 'none';
}
function hideAddForm(a,b,c){
    var divAddForm = document.getElementById(a);
    var divShowAdd = document.getElementById(b);
    var divHideAdd = document.getElementById(c);
    divAddForm.style.display='none';
    divHideAdd.style.display='none';
    divShowAdd.style.display = 'block';
}

function setHideAndShowEvents(){
    var buttonShowAddTopicsForm = document.getElementById('button-show-add-topics-form');
    var buttonHideAddTopicsForm = document.getElementById('button-hide-add-topics-form');
    //If No topics exist, these buttons are undefined.
    var buttonShowAddQuestionSetForm = document.getElementById('button-show-add-question-set-form');
    var buttonHideAddQuestionSetForm = document.getElementById('button-hide-add-question-set-form');

    buttonShowAddTopicsForm.addEventListener(
        'click',
        (function(a,b,c){return function(){showAddForm(a,b,c);}})('div-add-topics-form','div-show-add-topics','div-hide-add-topics'));

    buttonHideAddTopicsForm.addEventListener(
        'click',
        (function(a,b,c){return function(){hideAddForm(a,b,c);}})('div-add-topics-form','div-show-add-topics','div-hide-add-topics'));

    //Only need to add these if topics exist.
    if(buttonShowAddQuestionSetForm){
        buttonShowAddQuestionSetForm.addEventListener(
            'click',
            (function(a,b,c){return function(){showAddForm(a,b,c);}})('div-add-question-set-form','div-show-add-question-set','div-hide-add-question-set'));

        buttonHideAddQuestionSetForm.addEventListener(
            'click',
            (function(a,b,c){return function(){hideAddForm(a,b,c);}})('div-add-question-set-form','div-show-add-question-set','div-hide-add-question-set'));
    }
}

function collapsibleListHandler(){
    $('.list-group-item').on('click', function() {
        $('.glyphicon', this)
          .toggleClass('glyphicon-chevron-right')
          .toggleClass('glyphicon-chevron-down');
    });
}

$(document).ready(function(){
    setHideAndShowEvents();
    collapsibleListHandler();
});
