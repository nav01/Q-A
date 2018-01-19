/*
    Used to show the specific question type the user wants to create while
    hiding others. Desired behavior would be to have the forms load through
    ajax, but deform's ajax doesn't appear to work.
*/
$(document).ready(function(){
    var formCache = {};
    //Should only find one element, the rerendered form upon validation failure.
    var visibleForm = $('[id^=form-]');
    if (visibleForm.length > 0){
        visibleForm = visibleForm[0];
        let question_type = $(visibleForm).attr('id').replace('form-','');
        formCache[question_type] = visibleForm;
    } else {
        visibleForm = {style:{display:null}}; //Dummy initial 'form'
    }

    $('#question-form-request').submit(function(e){
        e.preventDefault();
        var form = this;
        var questionType = $(form).find('#select-question-type').val();
        if (formCache[questionType]) {
            $(visibleForm).hide();
            visibleForm = formCache[questionType];
            $(visibleForm).show();
        } else {
            console.log($(form).serialize());
            $.ajax({
                type: 'GET',
                url: $(form).attr('action'),
                data: $(form).serialize(),
            }).done(function(data) {
                var div ='<div id="form-' + questionType + '">';
                $(visibleForm).hide();
                visibleForm = $(div + data + '</div>');
                formCache[questionType] = visibleForm;
                $('.container').append(visibleForm);
            }).fail(function() {
                alert('failure');
            });
        }
    });
});
