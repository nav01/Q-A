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
