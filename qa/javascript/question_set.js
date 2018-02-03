$(document).ready(function() {
    $('#question-form-generation').hide();
    $('#div-hide-add-question').hide();
    $('#button-show-add-question').click(
        {a: 'question-form-generation' , b: 'div-show-add-question', c: 'div-hide-add-question'},
        showAddForm
    );

    $('#button-hide-add-question').click(
        {a: 'question-form-generation' , b: 'div-show-add-question', c: 'div-hide-add-question'},
        hideAddForm
    );
    //Check if there are any questions left, and delete the reorder button if not.
    $(window).on('deleteResource', function(e){
        if (!$('#question-list li').length) {
            $('#reorder').remove();
        }
    });
});
