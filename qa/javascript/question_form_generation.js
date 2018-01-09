/*
    Used to show the specific question type the user wants to create while
    hiding others. Desired behavior would be to have the forms load through
    ajax, but deform's ajax doesn't appear to work.
*/
window.onload = function(){
    let visibleForm = undefined;
    function showQuestionForm(){
        if(visibleForm) {
            visibleForm.style.display='none';
        }
        switch(this.options[this.selectedIndex].value) {
            case 'multiple-choice':
                visibleForm = document.getElementById('multiple-choice');
                visibleForm.style.display='block';
                break;
        }
    }
    var questionOptions = document.getElementById('question-controller');
    questionOptions.addEventListener('change', showQuestionForm);
}
