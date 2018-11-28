function TableHandler() {
    let rows = $('tbody tr', this);
    let rangeText = $('.rangeText', this);
    let rowsTotal = rows.length;
    let rowsRangeSelector = $('.rowsRangeSelector', this);
    let nextButton = $('.nextButton', this);
    let prevButton = $('.prevButton', this);
    let rowsRange = parseInt(rowsRangeSelector.val());
    let interval = [0, rowsRange];
    let handleButtons = function () {
        nextButton.attr('disabled', (interval[1] >= rowsTotal));
        prevButton.attr('disabled', interval[0] <= 0);
    };

    let handleText = function () {
        let upperBound = interval[1] <= rowsTotal ? interval[1] : rowsTotal;
        rangeText.text(interval[0] + '-' + upperBound + ' / ' + rowsTotal);
    };

    rows.each(function () {
        let row = $(this);
        let target = row.data('href');
        if (jQuery.type(target) !== "undefined") {
            $('td', this).not('.edit_object').click(function () {
                window.location.href = target;
            });
        }
    });
    rows.slice(interval[0], interval[1]).show();
    handleButtons();
    handleText();

    nextButton.click(function () {
        rows.slice(interval[0], interval[1]).hide();
        interval[0] += rowsRange;
        interval[1] += rowsRange;
        rows.slice(interval[0], interval[1]).show();
        handleButtons();
        handleText();
        console.log("<" + interval[0] + "," + interval[1] + ">");
    });

    prevButton.click(function () {
        rows.slice(interval[0], interval[1]).hide();
        if (interval[0] - rowsRange < 0) {
            interval[0] = 0;
            interval[1] = rowsRange;
        }
        else {
            interval[0] -= rowsRange;
            interval[1] -= rowsRange;
        }

        rows.slice(interval[0], interval[1]).show();
        handleButtons();
        handleText();
        console.log("<" + interval[0] + "," + interval[1] + ">");
    });

    rowsRangeSelector.change(function () {
        let newRange = parseInt(rowsRangeSelector.val());
        if (newRange > rowsRange) {
            let upperBound = interval[0] + newRange;
            rows.slice(interval[1], upperBound).show();
            interval[1] = upperBound;
        } else if (newRange < rowsRange) {
            let upperBound = interval[0] + newRange;
            rows.slice(upperBound, interval[1]).hide();
            interval[1] = upperBound;
        }
        rowsRange = newRange;
        handleButtons();
        handleText();
        console.log("<" + interval[0] + "," + interval[1] + ">");
    });
}

jQuery(document).ready(function ($) {
    let pagedTables = $('.pagedTable');
    pagedTables.each(TableHandler);
});