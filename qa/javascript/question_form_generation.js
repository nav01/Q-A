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

    $('.question-type').click(function(e){
        e.preventDefault();
        var link = this;
        var questionType = $(this).attr('data-type');
        if (formCache[questionType]) {
            $(visibleForm).hide();
            visibleForm = formCache[questionType];
            $(visibleForm).show();
        } else {
            $.ajax({
                type: 'GET',
                url: $(link).attr('href'),
                data: {type: questionType, question_set_id: window.location.pathname.split('/')[2]}
            }).done(function(data) {
                var div ='<div class="row col-lg-8 col-lg-offset-2" id="form-' + questionType + '">';
                $(visibleForm).hide();
                visibleForm = $(div + data + '</div>');
                formCache[questionType] = visibleForm;
                $('#question-form-generation').append(visibleForm);
            }).fail(function() {
                alert('failure');
            });
        }
    });
});
