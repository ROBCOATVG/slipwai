import java.util.ArrayList;
import java.util.List;

/** The admissions board: which beds are taken, and by whom. */
public final class Board {
    private final List<String> beds = new ArrayList<>();

    public void admit(String patient) {
        beds.add(patient);
    }

    public int occupied() {
        return beds.size();
    }

    public static void main(String[] args) {
        Board board = new Board();
        board.admit("first");
        System.out.println("occupied: " + board.occupied());
    }
}
